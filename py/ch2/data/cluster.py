from logging import getLogger

from math import log10
from sqlalchemy import desc, text

# absolute imports to allow invocation from non-root
from ch2.data import session
from ch2.sql import ActivityJournal, ClusterParameters, ClusterInputScratch
from ch2.sql.utils import add

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


def cluster_from_last_activity(s, radius):
    activity_journal = s.query(ActivityJournal).order_by(desc(ActivityJournal.start)).first()
    return cluster_from_activity(s, activity_journal, radius)


def cluster_from_activity(s, activity_journal, radius):
    return cluster_from_point(s, activity_journal.centre, activity_journal.utm_srid, radius)


def cluster_from_point(s, point, srid, radius):
    start = 1000
    exp = 2.0
    min_dbscan = 2
    min_total = 100
    target = 0.75
    buffer = 10
    indep = 4
    overlap = 0
    note = f'{start} {exp} auto {min_dbscan} {min_total} {target} {buffer} runs {indep}/{overlap}'
    parameters = add(s, ClusterParameters(srid=srid, centre=point, radius=radius, note=note))
    populate_tmp_lines(s, parameters, point, srid, radius, indep=indep, overlap=overlap)
    log.info(f'Starting {note}')
    eps = 20
    for log_nth in range(int(0.5 + log10(start) / log10(exp)), -1, -1):
        nth = int(0.5 + exp ** log_nth)
        cluster_remaining(s, parameters, nth, eps, min_dbscan, min_total, target, buffer)
    for nth in range(2, 6):
        eps = 10 * 2 ** nth
        cluster_remaining(s, parameters, -1 * nth, eps, min_dbscan, min_total, target, buffer)
    log.info(f'Finished {note}')
    return note


def cluster_remaining(s, parameters, nth, eps, min_dbscan, min_total, target, buffer):
    log.info(f'Grouping {parameters.note} at {nth}/{eps}')
    identify_groups(s, parameters, nth, eps, min_dbscan)
    label_all_geoms(s, parameters, nth, eps, min_dbscan, max(nth, 1) * min_total, target, buffer)


def identify_groups(s, parameters, nth, eps, min_dbscan):
    sql = text('''
  with groups as (select id,
                         st_clusterdbscan(geom, eps:=:eps, minpoints:=:min_dbscan) over () as "group"
                    from (select id,
                                 row_number() over () as i,
                                 geom
                            from cluster_input_scratch
                           where "group" is null
                             and cluster_parameters_id = :cluster_parameters_id
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
    s.connection().execute(sql, cluster_parameters_id=parameters.id, nth=nth, eps=eps, min_dbscan=min_dbscan)
    s.commit()


def label_all_geoms(s, parameters, nth, eps, min_dbscan, min_total, target, buffer):
    sql = text('''
  with points as (select st_dumppoints(geom) as point,
                         "group"
                    from cluster_input_scratch
                   where level = :nth
                     and cluster_parameters_id = :cluster_parameters_id),
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
insert into cluster_hull ("group", cluster_parameters_id, level, hull)
select cs."group", :cluster_parameters_id, :nth, cs.hull
  from census as cs
 where cs.n >= :min_total;
 
update cluster_input_scratch as c
   set "group" = h."group",
       level = h.level
  from cluster_hull as h
 where st_covers(h.hull, c.geom)
   and (c.level is null or c.level = h.level)
   and c.cluster_parameters_id = h.cluster_parameters_id
   and h.level = :nth
   and h.cluster_parameters_id = :cluster_parameters_id;
   
update cluster_input_scratch as c 
   set "group" = null,
       level = null
 where c.level = :nth
   and c.cluster_parameters_id = :cluster_parameters_id
   and c."group" not in (
       select "group" from cluster_hull where cluster_parameters_id = :cluster_parameters_id and level = :nth)
    ''')
    log.debug(sql)
    s.connection().execute(sql, cluster_parameters_id=parameters.id, nth=nth, eps=eps, min_dbscan=min_dbscan,
                           min_total=min_total, target=target, buffer=buffer)
    s.commit()


def populate_tmp_lines(s, parameters, point, srid, radius, indep=1, overlap=0):
    '''
    segments of length indep+overlap, where indep points are independent and overlap points overlap.
    indep=1 overlap=0 - each point is separate  o o o o
    indep=2 overlap=0 - pairs  o-o o-o o-o
    indep=2 overlap=1 - overlapping triplets o-o-O-o-o-O-o-o-O
    '''
    s.query(ClusterInputScratch).delete(synchronize_session=False)
    sql = text('''
  with lines as (select id, 
                        st_transform(route::geometry, :srid) as line
                   from activity_journal
                  where st_distance(:point, centre) < :radius),
       lengths as (select id, st_npoints(line) - :indep - :overlap as length from lines),
       series as (select id, generate_series(1, length, :indep) as series from lengths),
       pairs as (select st_makeline(st_pointn(line, series), st_pointn(line, series + :indep + :overlap)) as pair
                   from series inner join lines on lines.id = series.id)
insert into cluster_input_scratch (geom, cluster_parameters_id)
select pair, :cluster_parameters_id
  from pairs;  
''')
    log.debug(sql)
    s.connection().execute(sql, cluster_parameters_id=parameters.id, point=str(point), srid=srid, radius=radius,
                           indep=indep, overlap=overlap)
    s.commit()


if __name__ == '__main__':
    s = session('-v5')
    cluster_from_last_activity(s, 200000)
