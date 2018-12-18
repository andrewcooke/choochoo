
from collections import defaultdict

import pandas as pd
from sqlalchemy import inspect, select
from sqlalchemy.sql.functions import coalesce

from ..squeal.database import connect
from ..squeal import ActivityJournal, StatisticName, StatisticJournal, StatisticJournalInteger, \
    StatisticJournalFloat, StatisticJournalText, Interval, StatisticMeasure, Source
from ..squeal.types import short_cls
from ..stoats.read.segment import SegmentImporter
from ..stoats.waypoint import WaypointReader


LOG = [None]


def df(query):
    # https://stackoverflow.com/questions/29525808/sqlalchemy-orm-conversion-to-pandas-dataframe
    return pd.read_sql(query.statement, query.session.bind)


def session(*args):
    ns, log, db = connect(args)
    LOG[0] = log
    return db.session()


def log():
    if not LOG[0]:
        raise Exception('Create session first')
    return LOG[0]


def waypoints(s, activity_journal_id, *statistics, owner=short_cls(SegmentImporter)):
    names = dict((statistic, statistic) for statistic in statistics)
    # int() to convert numpy types
    ajournal = s.query(ActivityJournal).filter(ActivityJournal.id == int(activity_journal_id)).one()
    return pd.DataFrame(WaypointReader(log(), with_timespan=False).read(s, ajournal, names, owner))


def _collect_statistics(s, names):
    if not names:
        names = ['%']
    statistic_ids, statistic_names = set(), set()
    for name in names:
        for statistic_name in s.query(StatisticName). \
                filter(StatisticName.name.like(name)).all():
            statistic_ids.add(statistic_name.id)
            statistic_names.add(statistic_name.name)
    return statistic_names, statistic_ids


def _build_statistic_journal_query(statistic_ids, start, finish, owner, constraint, source_ids, schedule):

    # use more efficient expression interface and exploit the fact that
    # alternative journal types will be null in an outer join.

    sj = inspect(StatisticJournal).local_table
    sn = inspect(StatisticName).local_table
    sji = inspect(StatisticJournalInteger).local_table
    sjf = inspect(StatisticJournalFloat).local_table
    sjt = inspect(StatisticJournalText).local_table
    inv = inspect(Interval).local_table

    q = select([sn.c.name, sj.c.time, coalesce(sjf.c.value, sji.c.value, sjt.c.value)]). \
        select_from(sj.join(sn).outerjoin(sjf).outerjoin(sji).outerjoin(sjt)). \
        where(sn.c.id.in_(statistic_ids))
    if start:
        q = q.where(sj.c.time >= start)
    if finish:
        q = q.where(sj.c.time <= finish)
    if owner:
        q = q.where(sn.c.owner == owner)
    if constraint:
        q = q.where(sn.c.constraint == constraint)
    if source_ids is not None:  # avoid testing DataFrame sequences as bools
        # int() to convert numpy types
        q = q.where(sj.c.source_id.in_(int(id) for id in source_ids))
    if schedule:
        q = q.join(inv).where(inv.c.schedule == schedule)
    q = q.order_by(sj.c.time)
    return q


class MissingData(Exception): pass


def statistics(s, *statistics,
               start=None, finish=None, owner=None, constraint=None, source_ids=None, schedule=None):
    statistic_names, statistic_ids = _collect_statistics(s, statistics)
    q = _build_statistic_journal_query(statistic_ids, start, finish, owner, constraint, source_ids, schedule)
    data, times, err_cnt = defaultdict(list), [], defaultdict(lambda: 0)

    def pad():
        nonlocal data, times
        n = len(times)
        for name in statistic_names:
            if len(data[name]) != n:
                err_cnt[name] += 1
                if err_cnt[name] <= 1:
                    log().warning('Missing %s at %s (single warning)' % (name, times[-1]))
                data[name].append(None)

    for name, time, value in s.connection().execute(q):
        if times and times[-1] != time:
            pad()
        if not times or times[-1] != time:
            times.append(time)
        if len(data[name]) >= len(times):
            raise Exception('Duplicate data for %s at %s ' % (name, time) +
                            '(you may need to specify more constraints to make the query unique)')
        data[name].append(value)
    pad()
    return pd.DataFrame(data, index=times)


def statistic_quartiles(s, *statistics, schedule='m',
                        start=None, finish=None, owner=None, constraint=None, source_ids=None):
    statistic_names, statistic_ids = _collect_statistics(s, statistics)
    q = s.query(StatisticMeasure). \
        join(StatisticJournal, StatisticMeasure.statistic_journal_id == StatisticJournal.id). \
        join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
        join(Source, StatisticJournal.source_id == Source.id). \
        filter(StatisticName.id.in_(statistic_ids)). \
        filter(StatisticMeasure.quartile != None)
    if start:
        q = q.filter(StatisticJournal.time >= start)
    if finish:
        q = q.filter(StatisticJournal.time <= finish)
    if owner:
        q = q.filter(StatisticName.owner == owner)
    if constraint:
        q = q.filter(StatisticName.constraint == constraint)
    if source_ids is not None:
        q = q.filter(StatisticJournal.source_id.in_(source_ids))
    if schedule:
        q = q.join((Interval, StatisticMeasure.source_id == Interval.id)). \
            filter(Interval.schedule == schedule)
    log().debug(q)
    raw_data = defaultdict(lambda: defaultdict(lambda: [0] * 5))
    for measure in q.all():
        raw_data[measure.source.start][measure.statistic_journal.statistic_name.name][measure.quartile] = \
            measure.statistic_journal.value
    data, times = defaultdict(list), []
    for time in sorted(raw_data.keys()):
        times.append(time)
        sub_data = raw_data[time]
        for statistic in statistic_names:
            if statistic in sub_data:
                data[statistic].append(sub_data[statistic])
            else:
                data[statistic].append(None)
    return pd.DataFrame(data, index=times)

