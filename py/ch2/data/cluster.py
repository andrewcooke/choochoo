from math import log10
from logging import getLogger

from geoalchemy2 import Geometry
from sqlalchemy import func, cast, desc, literal, text

# absolute imports to allow invocation from non-root
from ch2.data import session
from ch2.sql import ClusterTmp, StatisticJournalPoint, ActivityJournal, Cluster

log = getLogger(__name__)


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
    tag = f'{start} {exp} auto {min_dbscan} {min_total} {target} {buffer}'
    assert_tag(s, tag)
    populate_tmp(s, tag, point, srid, radius)
    log.info(f'Starting {tag}')
    eps = 20
    for log_nth in range(int(0.5 + log10(start) / log10(exp)), -1, -1):
        nth = int(0.5 + exp ** log_nth)
        cluster_remaining(s, tag, nth, eps, min_dbscan, min_total, target, buffer)
    for nth in range(2, 6):
        eps = 10 * 2 ** nth
        cluster_remaining(s, tag, -1 * nth, eps, min_dbscan, min_total, target, buffer)
    filter_extended(s, tag)
    log.info(f'Finished {tag}')
    return tag


def cluster_remaining(s, tag, nth, eps, min_dbscan, min_total, target, buffer):
    log.info(f'Grouping {tag} at {nth}/{eps}')
    # import pdb; pdb.set_trace()
    identify_groups(s, tag, nth, eps, min_dbscan)
    label_all_points(s, tag, nth, eps, min_dbscan, max(nth, 1) * min_total, target, buffer)


def identify_groups(s, tag, nth, eps, min_dbscan):
    sql = text('''
  with groups as (select id,
                         st_clusterdbscan(point, eps:=:eps, minpoints:=:min_dbscan) over () as "group"
                    from (select id,
                                 row_number() over () as i,
                                 point
                            from cluster_tmp
                           where "group" is null
                             and tag = :tag
                           order by id) as x
                   where i % greatest(:nth, 1) = 0)
update cluster_tmp
   set "group" = groups."group",
       level = :nth
  from groups
 where cluster_tmp.id = groups.id
   and groups."group" is not null;
''')
    log.debug(sql)
    s.connection().execute(sql, tag=tag, nth=nth, eps=eps, min_dbscan=min_dbscan)
    s.commit()


def label_all_points(s, tag, nth, eps, min_dbscan, min_total, target, buffer):
    sql = text('''
  with hulls as (select st_buffer(st_concavehull(st_collect(point), :target), :buffer) as hull,
                        "group"
                   from cluster_tmp
                  where level = :nth
                    and tag = :tag
                  group by "group"),
       census as (select count(c.point) as n,
                         h."group",
                         h.hull
                    from cluster_tmp as c,
                         hulls as h
                   where st_covers(h.hull, c.point)
                     and (c."group" = h."group" or c."group" is null)
                   group by h.hull, h."group"
                   order by count(c.point) desc)
insert into cluster ("group", tag, level, hull)
select cs."group", :tag, :nth, cs.hull
  from census as cs
 where cs.n >= :min_total;
 
update cluster_tmp as c
   set "group" = h."group",
       level = h.level
  from cluster as h
 where st_covers(h.hull, c.point)
   and (c.level is null or c.level = h.level)
   and c.tag = h.tag
   and h.level = :nth
   and h.tag = :tag;
   
update cluster_tmp as c 
   set "group" = null,
       level = null
 where c.level = :nth
   and c.tag = :tag
   and c."group" not in (select "group" from cluster where tag = :tag and level = :nth)
    ''')
    log.debug(sql)
    s.connection().execute(sql, tag=tag, nth=nth, eps=eps, min_dbscan=min_dbscan, min_total=min_total,
                           target=target, buffer=buffer)
    s.commit()


def filter_extended(s, tag):
    sql = text('''
  with areas as (select c.tag,
                        c.level, 
                        c."group",
                        st_area(c.hull) / count(t.point) as area
                   from cluster as c,
                        cluster_tmp as t
                  where c.tag = t.tag
                    and c."group" = t."group"
                    and c.level = t.level
                    and c.tag = :tag
                  group by c.tag, c.level, c."group", c.hull)
delete from cluster
 where (tag, level, "group") in (select a.tag, a.level, a."group" from areas as a where a.area > 1000);
''')
    log.debug(sql)
    s.connection().execute(sql, tag=tag)
    s.commit()


def assert_tag(s, tag):
    if s.query(Cluster).filter(Cluster.tag == tag).count():
        raise Exception(f'ClusterHull tag {tag} already exists')


def populate_tmp(s, tag, point, srid, radius):
    s.query(ClusterTmp).delete(synchronize_session=False)
    query = s.query(literal(tag),
                    StatisticJournalPoint.id,
                    func.ST_Transform(cast(StatisticJournalPoint.value, Geometry), srid)). \
        filter(func.ST_Distance(point, StatisticJournalPoint.value) < radius)
    table = ClusterTmp.__table__
    insert = table.insert().from_select([table.c.tag, table.c.statistic_id, table.c.point], query)
    log.debug(insert)
    s.execute(insert)
    s.commit()


if __name__ == '__main__':
    s = session('-v5')
    cluster_from_last_activity(s, 200000)
