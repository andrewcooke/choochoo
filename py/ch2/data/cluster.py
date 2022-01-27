from collections import namedtuple
from logging import getLogger

from geoalchemy2.shape import to_shape
from math import log10
from sqlalchemy import desc, text
from sqlalchemy.exc import InternalError

from ..data.sector import add_start_finish
from ..sql import ActivityJournal, ClusterInputScratch, ClusterHull, ClusterFragmentScratch, SectorGroup, Sector
from ..sql.tables.sector import SectorType
from ..sql.types import short_cls

log = getLogger(__name__)


'''
what do we want to do here?
somehow we want to automatically identify segments of a ride.
what is a segment?
one answer is to construct a graph of rides where intersections between paths are nodes.
then a segment is an edge between two nodes (or possibly a popular series of edges).
how do we construct that graph?  
or even something vaguely similar?
these notes are written in retrospect (in a pause during development).
this work was not done in response to a simple analysis - it was an exploration of what is possible.
if we treat all the gps points as a cloud of data then we can 
1 - find the densest regions by doing cluster analysis on a sparse sample of data
2 - iteratively find less dense regions by sampling more frequently
3 - once we are sampling all points, we can relax conditions to fill in what is left
this gives us a hierarchy of clusters.
is that enough to construct the graph?
i don't know - i haven't got that far yet.
the above process is slow and noisy - how can we improve it?
one idea is to use small line segments rather than points,
this requires surprisingly little modification of the code. 
it runs faster and produces fewer clusters (with similar total coverage) but is not so great at infrequently used routes.
maybe the infrequent routes don't matter so much?
in general, the larger the segment, the faster the time but the lower the resolution.
having an overlap seems to help 'semantic' groups.
once we have local clusters, find 'typical' routes and then group by those?
'''


def hulls_from_last_activity(s, radius_km):
    activity_journal = s.query(ActivityJournal). \
        filter(ActivityJournal.centre != None). \
        order_by(desc(ActivityJournal.start)).first()
    if activity_journal:
        return hulls_from_activity(s, activity_journal, radius_km)
    else:
        log.warning('No activities, so no clusters (no sector group)')


def hulls_from_activity(s, activity_journal, radius_km):
    return hulls_from_point(s, activity_journal.centre, radius_km,
                            title=f'From activity {activity_journal.start}')


Parameters = namedtuple('Parameters', 'start,exp,min_dbscan,min_total,target,buffer,indep,overlap',
                        defaults=(1000, 2.0, 2, 100, 0.75, 10, 4, 0))


def hulls_from_point(s, centre, radius_km, title, parameters=Parameters()):
    sector_group = SectorGroup.add(s, to_shape(centre).coords[0], radius_km, title)
    log.info(f'Starting clustering for {sector_group.title}')
    delete_tmp_lines(s, sector_group)
    populate_tmp_lines(s, sector_group, parameters)
    delete_hulls(s, sector_group)
    eps = 20
    for log_nth in range(int(0.5 + log10(parameters.start) / log10(parameters.exp)), -1, -1):
        nth = int(0.5 + parameters.exp ** log_nth)
        cluster_remaining(s, sector_group, parameters, nth, eps)
    for nth in range(2, 6):
        eps = 10 * 2 ** nth
        cluster_remaining(s, sector_group, parameters, -1 * nth, eps)
    log.info(f'Finished clustering for {sector_group.title}')
    delete_tmp_lines(s, sector_group)
    return sector_group


def delete_hulls(s, sector_group):
    query = s.query(ClusterHull).filter(ClusterHull.sector_group_id == sector_group.id)
    n = query.count()
    if n:
        log.warning(f'Deleting {n} hulls for {sector_group.title}')
        query.delete(synchronize_session=False)


def cluster_remaining(s, sector_group, parameters, nth, eps):
    log.info(f'Grouping at {nth}/{eps}')
    identify_groups(s, sector_group, parameters, nth, eps)
    label_all_geoms(s, sector_group, parameters, nth, eps, max(nth, 1) * parameters.min_total)


def identify_groups(s, sector_group, parameters, nth, eps):
    sql = text('''
  with groups as (select id,
                         st_clusterdbscan(geom, eps:=:eps, minpoints:=:min_dbscan) over () as "group"
                    from (select id,
                                 row_number() over () as i,
                                 geom
                            from cluster_input_scratch
                           where "group" is null
                             and sector_group_id = :sector_group_id
                           order by id) as x
                   where i % greatest(:nth, 1) = 0)
update cluster_input_scratch
   set "group" = groups."group",
       level = :nth
  from groups
 where cluster_input_scratch.id = groups.id
   and groups."group" is not null;
''')
    log.debug(sql)
    s.connection().execute(sql, sector_group_id=sector_group.id, nth=nth, eps=eps,
                           min_dbscan=parameters.min_dbscan)
    s.commit()


def label_all_geoms(s, sector_group, parameters, nth, eps, min_total):
    sql = text('''
  with points as (select st_dumppoints(geom) as point,
                         "group"
                    from cluster_input_scratch
                   where level = :nth
                     and sector_group_id = :sector_group_id),
       hulls as (select st_buffer(st_concavehull(st_collect((point).geom), :target), :buffer) as hull,
                        "group"
                   from points
                  group by "group"),
       census as (select count(c.geom) as n,
                         h."group",
                         h.hull
                    from cluster_input_scratch as c,
                         hulls as h
                   where st_covers(h.hull, c.geom)
                     and (c."group" = h."group" or c."group" is null)
                   group by h.hull, h."group"
                   order by count(c.geom) desc)
insert into cluster_hull ("group", sector_group_id, level, hull)
select cs."group", :sector_group_id, :nth, cs.hull
  from census as cs
 where cs.n >= :min_total;
 
update cluster_input_scratch as c
   set "group" = h."group",
       level = h.level
  from cluster_hull as h
 where st_covers(h.hull, c.geom)
   and (c.level is null or c.level = h.level)
   and c.sector_group_id = h.sector_group_id
   and h.level = :nth
   and h.sector_group_id = :sector_group_id;
   
update cluster_input_scratch as c 
   set "group" = null,
       level = null
 where c.level = :nth
   and c.sector_group_id = :sector_group_id
   and c."group" not in (
       select "group" from cluster_hull where sector_group_id = :sector_group_id and level = :nth)
    ''')
    log.debug(sql)
    s.connection().execute(sql, sector_group_id=sector_group.id, nth=nth, eps=eps,
                           min_dbscan=parameters.min_dbscan, min_total=min_total,
                           target=parameters.target, buffer=parameters.buffer)
    s.commit()


def populate_tmp_lines(s, sector_group, parameters):
    '''
    segments of length indep+overlap, where indep points are independent and overlap points overlap.
    indep=1 overlap=0 - each point is separate  o o o o
    indep=2 overlap=0 - pairs  o-o o-o o-o
    indep=2 overlap=1 - overlapping triplets o-o-O-o-o-O-o-o-O
    '''
    sql = text('''
  with lines as (select aj.id, 
                        st_force3dm(st_transform(aj.route_et::geometry, sg.srid)) as line
                   from activity_journal as aj,
                        sector_group as sg
                  where sg.id = :sector_group_id
                    and st_distance(sg.centre, aj.centre) < sg.radius),
       lengths as (select id, st_npoints(line) - :indep - :overlap as length from lines),
       series as (select id, generate_series(1, length, :indep) as series from lengths),
       pairs as (select st_makeline(st_pointn(line, series), st_pointn(line, series + :indep + :overlap)) as pair
                   from series inner join lines on lines.id = series.id)
insert into cluster_input_scratch (geom, sector_group_id)
select pair, :sector_group_id
  from pairs;  
''')
    log.debug(sql)
    s.connection().execute(sql, sector_group_id=sector_group.id, indep=parameters.indep, overlap=parameters.overlap)
    s.commit()


def delete_tmp_lines(s, sector_group):
    s.query(ClusterInputScratch). \
        filter(ClusterInputScratch.sector_group_id == sector_group.id). \
        delete(synchronize_session=False)


def sectors_from_hulls(s, sector_group):
    from ..pipeline.calculate.cluster import ClusterCalculator
    log.info(f'Finding sectors for clusters for {sector_group.title}')
    delete_tmp_fragments(s, sector_group)
    populate_tmp_fragments_from_hulls(s, sector_group)
    delete_sectors(s, sector_group)
    identify_sectors(s, sector_group)
    for id in s.query(Sector.id). \
            filter(Sector.sector_group_id == sector_group.id,
                   Sector.start == None,
                   Sector.finish == None,
                   Sector.owner == short_cls(ClusterCalculator)).all():
        try:
            add_start_finish(s, id[0])
        except InternalError as e:
            log.warning(f'Failed to generate sector {id}: {e}')
    delete_failed_sectors(s, sector_group)
    delete_tmp_fragments(s, sector_group)
    log.info(f'Finished finding sectors for clusters for {sector_group.title}')


def delete_failed_sectors(s, sector_group):
    from ..pipeline.calculate.cluster import ClusterCalculator
    query = s.query(Sector.id). \
            filter(Sector.sector_group_id == sector_group.id,
                   Sector.start == None,
                   Sector.finish == None,
                   Sector.owner == short_cls(ClusterCalculator))
    n = query.count()
    if n:
        log.warning(f'Cleaning out {n} failed sectors')
        query.delete(synchronize_session=False)


def populate_tmp_fragments_from_hulls(s, sector_group, min_separation=50):
    sql = text('''
  with route as (select st_transform(route_a::geometry, sg.srid) as route,
                        aj.id as activity_journal_id
                   from activity_journal as aj,
                        sector_group as sg
                  where sg.id = :sector_group_id
                    and st_distance(aj.centre, sg.centre) < sg.radius),
       straight as (select (st_dump(st_multi(st_locatebetween(r.route, -2, 2)))).geom as straight,
                           r.route,
                           r.activity_journal_id
                      from route as r),
       fragment2d as (select (st_dump(st_intersection(s.straight, c.hull))).geom as fragment,
                             s.activity_journal_id,
                             c.id as cluster_hull_id,
                             s.route as route
                        from straight as s,
                             cluster_hull as c
                       where st_intersects(s.straight, c.hull)
                         and c.sector_group_id = :sector_group_id),
       startend as (select activity_journal_id,
                           cluster_hull_id,
                           route,
                           fragment,
                           st_linelocatepoint(route, st_startpoint(fragment)) as a,
                           st_linelocatepoint(route, st_endpoint(fragment)) as b
                      from fragment2d),
       fragment3d as (select activity_journal_id,
                             cluster_hull_id,
                             st_linesubstring(route,
                                              least(1, greatest(0, least(a, b))),
                                              least(1, greatest(0, greatest(a, b)))) as fragment
                        from startend),
       lines3d as (select activity_journal_id,
                          cluster_hull_id,
                          fragment
                     from fragment3d
                    where st_geometrytype(fragment) = 'ST_LineString'
                      and st_distance(st_startpoint(fragment), st_endpoint(fragment)) > :min_separation)
insert into cluster_fragment_scratch (cluster_hull_id, activity_journal_id, fragment, length)
select distinct cluster_hull_id, activity_journal_id, fragment, st_length(fragment)
  from lines3d;
    ''')
    log.debug(sql)
    s.connection().execute(sql, sector_group_id=sector_group.id, min_separation=min_separation)
    s.commit()


def delete_tmp_fragments(s, sector_group):
    cluster_hull_ids = s.query(ClusterHull.id). \
        filter(ClusterHull.sector_group_id == sector_group.id)
    s.query(ClusterFragmentScratch). \
        filter(ClusterFragmentScratch.cluster_hull_id.in_(cluster_hull_ids)). \
        delete(synchronize_session=False)


def delete_sectors(s, sector_group):
    from ..pipeline.calculate.cluster import ClusterCalculator
    query = s.query(Sector). \
        filter(Sector.sector_group_id == sector_group.id,
               Sector.owner == short_cls(ClusterCalculator))
    n = query.count()
    if n:
        log.warning(f'Deleting {n} sectors for clusters in {sector_group.title}')
        query.delete(synchronize_session=False)


def identify_sectors(s, sector_group):
    from ..pipeline.calculate.cluster import ClusterCalculator
    sql = text('''
  with median as (select cfs.cluster_hull_id,
                         percentile_disc(0.75) within group (order by cfs.length) as length,
                         count(cfs.id) as n
                    from cluster_fragment_scratch as cfs,
                         cluster_hull as ch
                   where cfs.cluster_hull_id = ch.id
                     and ch.sector_group_id = :sector_group_id
                   group by cluster_hull_id),
       typical as (select f.activity_journal_id as activity_journal_id,
                          m.cluster_hull_id,
                          m.length,
                          f.fragment
                     from median as m,
                          cluster_fragment_scratch as f
                    where m.cluster_hull_id = f.cluster_hull_id
                      and m.length = f.length
                      and n > 2
                      and m.length > 500)
insert into sector (type, sector_group_id, route, distance, owner)
select :sector_type, :sector_group_id, st_force2d(fragment), length / 1000, :owner
  from typical;
''')
    log.debug(sql)
    s.connection().execute(sql, sector_group_id=sector_group.id, sector_type=SectorType.SECTOR,
                           owner=short_cls(ClusterCalculator))
    s.commit()

