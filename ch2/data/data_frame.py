
from collections import defaultdict

import pandas as pd
from sqlalchemy import inspect, select, and_
from sqlalchemy.sql.functions import coalesce

from ch2.lib.data import MutableAttr, kargs_to_attr
from ch2.squeal import ActivityJournal
from ..squeal import StatisticName, StatisticJournal, StatisticJournalInteger, \
    StatisticJournalFloat, StatisticJournalText, Interval, StatisticMeasure, Source
from ..squeal.database import connect, ActivityTimespan

# because this is intended to be called from jupyter we hide the log here
# other callers can use these routines by calling set_log() first.
LOG = [None]


def df(query):
    # https://stackoverflow.com/questions/29525808/sqlalchemy-orm-conversion-to-pandas-dataframe
    return pd.read_sql(query.statement, query.session.bind)


def session(*args):
    ns, log, db = connect(args)
    set_log(log)
    return db.session()


def get_log():
    if not LOG[0]:
        raise Exception('Create session first (or call set_log from within python)')
    return LOG[0]


def set_log(log):
    LOG[0] = log


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


def _tables():
    return kargs_to_attr(sj=inspect(StatisticJournal).local_table,
                         sn=inspect(StatisticName).local_table,
                         sji=inspect(StatisticJournalInteger).local_table,
                         sjf=inspect(StatisticJournalFloat).local_table,
                         sjt=inspect(StatisticJournalText).local_table,
                         inv=inspect(Interval).local_table,
                         at=inspect(ActivityTimespan).local_table)


def _build_statistic_journal_query(statistic_ids, start, finish, owner, constraint, source_ids, schedule):

    # use more efficient expression interface and exploit the fact that
    # alternative journal types will be null in an outer join.

    t = _tables()

    q = select([t.sn.c.name, t.sj.c.time, coalesce(t.sjf.c.value, t.sji.c.value, t.sjt.c.value)]). \
        select_from(t.sj.join(t.sn).outerjoin(t.sjf).outerjoin(t.sji).outerjoin(t.sjt)). \
        where(t.sn.c.id.in_(statistic_ids))
    if start:
        q = q.where(t.sj.c.time >= start)
    if finish:
        q = q.where(t.sj.c.time <= finish)
    if owner:
        q = q.where(t.sn.c.owner == owner)
    if constraint:
        q = q.where(t.sn.c.constraint == constraint)
    if source_ids is not None:  # avoid testing DataFrame sequences as bools
        # int() to convert numpy types
        q = q.where(t.sj.c.source_id.in_(int(id) for id in source_ids))
    if schedule:
        q = q.join(t.inv).where(t.inv.c.schedule == schedule)
    q = q.order_by(t.sj.c.time)
    return q


class MissingData(Exception): pass


def make_pad(data, times, statistic_names):
    err_cnt = defaultdict(lambda: 0)

    def pad():
        nonlocal data, times
        n = len(times)
        for name in statistic_names:
            if len(data[name]) != n:
                err_cnt[name] += 1
                if err_cnt[name] <= 1:
                    get_log().warning('Missing %s at %s (single warning)' % (name, times[-1]))
                data[name].append(None)

    return pad


def statistics(s, *statistics,
               start=None, finish=None, owner=None, constraint=None, source_ids=None, schedule=None):
    statistic_names, statistic_ids = _collect_statistics(s, statistics)
    q = _build_statistic_journal_query(statistic_ids, start, finish, owner, constraint, source_ids, schedule)
    data, times = defaultdict(list), []
    pad = make_pad(data, times, statistic_names)

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


def _resolve_activity(s, time, activity_journal_id):
    if activity_journal_id:
        if time:
            raise Exception('Specify activity_journal_id or time (not both)')
    else:
        if not time:
            raise Exception('Specify activity_journal_id or time')
        activity_journal_id = s.query(ActivityJournal.id). \
            filter(ActivityJournal.start <= time,
                   ActivityJournal.finish >= time).scalar()
        get_log().info('Using activity_journal_id=%d' % activity_journal_id)
    return activity_journal_id


def activity_statistics(s, *statistics,
                        time=None, activity_journal_id=None, with_timespan=False):

    statistic_names, statistic_ids = _collect_statistics(s, statistics)
    get_log().debug('Statistics IDs %s' % statistic_ids)
    activity_journal_id = _resolve_activity(s, time, activity_journal_id)

    t = _tables()
    q = select([t.sn.c.name, t.sj.c.time, coalesce(t.sjf.c.value, t.sji.c.value, t.sjt.c.value), t.at.c.id]). \
        select_from(t.sj.join(t.sn).outerjoin(t.sjf).outerjoin(t.sji).outerjoin(t.sjt)). \
        where(and_(t.sn.c.id.in_(statistic_ids), t.sj.c.source_id == activity_journal_id)). \
        select_from(t.at). \
        where(and_(t.at.c.start <= t.sj.c.time, t.at.c.finish >= t.sj.c.time,
                   t.at.c.activity_journal_id == activity_journal_id)). \
        order_by(t.sj.c.time)
    get_log().debug(q)

    data, times = defaultdict(list), []
    pad = make_pad(data, times, statistic_names)

    for name, time, value, timespan in s.connection().execute(q):
        if times and times[-1] != time:
            pad()
        if not times or times[-1] != time:
            times.append(time)
            if with_timespan:
                data['timespan_id'].append(timespan)
        if len(data[name]) >= len(times):
            raise Exception('Duplicate data for %s at %s ' % (name, time) +
                            '(you may need to specify more constraints to make the query unique)')
        data[name].append(value)
    pad()
    return pd.DataFrame(data, index=times)


def statistic_quartiles(s, *statistics,
                        start=None, finish=None, owner=None, constraint=None, source_ids=None, schedule=None):
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
    get_log().debug(q)

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


if __name__ == '__main__':
    s = session('-v 5')
    df = activity_statistics(s, 'Speed', time='2019-01-05 14:40:00', with_timespan=True)
    print(df.describe)
