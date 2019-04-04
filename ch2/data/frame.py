
import datetime as dt
from collections import defaultdict, Counter
from collections.abc import Mapping, Sequence
from logging import getLogger

import numpy as np
import pandas as pd
from sqlalchemy import inspect, select, and_, or_, alias, distinct
from sqlalchemy.sql.functions import coalesce, func

from ..lib.data import kargs_to_attr
from ..lib.date import local_time_to_time, time_to_local_time, YMD, HMS
from ..squeal import StatisticName, StatisticJournal, StatisticJournalInteger, ActivityJournal, \
    StatisticJournalFloat, StatisticJournalText, Interval, StatisticMeasure, Source
from ..squeal.database import connect, ActivityTimespan, ActivityGroup, ActivityBookmark, StatisticJournalType, \
    Composite, CompositeComponent
from ..stoats.display.nearby import nearby_any_time
from ..stoats.names import DISTANCE_KM, SPEED_KMH, MED_SPEED_KMH, MED_HR_IMPULSE_10, MED_CADENCE, \
    ELEVATION_M, CLIMB_MS, LOG_FITNESS, LOG_FATIGUE, ACTIVE_TIME_H, ACTIVE_DISTANCE_KM, MED_POWER_W, \
    TIMESPAN_ID, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, MED_WINDOW, \
    ELEVATION, SPEED, HR_ZONE, HR_IMPULSE_10, ALTITUDE, CADENCE, TIME, LOCAL_TIME, FITNESS, FATIGUE, REST_HR, \
    DAILY_STEPS, ACTIVE_TIME, ACTIVE_DISTANCE, POWER, INDEX
from ..uranus.coasting import CoastingBookmark

log = getLogger(__name__)


def df(query):
    # https://stackoverflow.com/questions/29525808/sqlalchemy-orm-conversion-to-pandas-dataframe
    return pd.read_sql(query.statement, query.session.bind)


def session(*args):
    ns, db = connect(args)
    return db.session()


def _add_constraint(q, attribute, value, key):
    if value is not None:
        if isinstance(value, Mapping):
            if key in value:
                q = q.filter(attribute == value[key])
        elif isinstance(value, str):
            q = q.filter(attribute == value)
        elif isinstance(value, Sequence):
            q = q.filter(attribute.in_(value))
        else:
            q = q.filter(attribute == value)
    return q


def _collect_statistics(s, names, owner=None, constraint=None):
    if not names:
        names = ['%']
    statistic_ids, statistic_names = set(), set()
    for name in names:
        q = s.query(StatisticName).filter(StatisticName.name.like(name))
        q = _add_constraint(q, StatisticName.owner, owner, name)
        q = _add_constraint(q, StatisticName.constraint, constraint, name)
        for statistic_name in q.all():
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
                         at=inspect(ActivityTimespan).local_table,
                         cmp=inspect(Composite).local_table,
                         cc=inspect(CompositeComponent).local_table,
                         src=inspect(Source).local_table)


def _build_statistic_journal_query(statistic_ids, start, finish, source_ids, schedule):

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
    if source_ids is not None:  # avoid testing DataFrame sequences as bools
        # int() to convert numpy types
        q = q.where(t.sj.c.source_id.in_(int(id) for id in source_ids))
    if schedule:
        q = q.join(t.inv).where(t.inv.c.schedule == schedule)
    q = q.order_by(t.sj.c.time)
    return q


class MissingData(Exception): pass


def make_pad(data, times, statistic_names, quiet=False):
    err_cnt = defaultdict(lambda: 0)

    def pad():
        nonlocal data, times
        n = len(times)
        for name in statistic_names:
            if len(data[name]) != n:
                err_cnt[name] += 1
                if err_cnt[name] <= 1 and not quiet:
                    log.warning('Missing %s at %s (single warning)' % (name, times[-1]))
                data[name].append(None)

    return pad


def old_statistics(s, *statistics, start=None, finish=None, owner=None, constraint=None, source_ids=None,
               schedule=None, quiet=False):

    statistic_names, statistic_ids = _collect_statistics(s, statistics, owner, constraint)
    q = _build_statistic_journal_query(statistic_ids, start, finish, source_ids, schedule)
    data, times = defaultdict(list), []
    pad = make_pad(data, times, statistic_names, quiet=quiet)

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


def resolve_activity(s, local_time=None, time=None, activity_journal_id=None,
                     activity_group_name=None, activity_group_id=None):
    '''
    If activity_journal_id is given, it is returned.

    Otherwise, specify one of (local_time, time) and one of (activity_group_name, activity_group_id).
    '''

    if activity_journal_id:
        return activity_journal_id
    if local_time:
        time = local_time_to_time(local_time)
    if not time:
        raise Exception('Specify activity_journal_id or time')
    if activity_group_name:
        activity_group_id = s.query(ActivityGroup.id).filter(ActivityGroup.name == activity_group_name).scalar()
    if not activity_group_id:
        raise Exception('Specify activity_group_id or activity_group_name')
    activity_journal_id = s.query(ActivityJournal.id). \
        filter(ActivityJournal.start <= time,
               ActivityJournal.finish >= time,
               ActivityJournal.activity_group_id == activity_group_id).scalar()
    log.info('Using activity_journal_id=%d' % activity_journal_id)
    return activity_journal_id


def activity_statistics(s, *statistics, owner=None, constraint=None, start=None, finish=None,
                        local_time=None, time=None, bookmarks=None, activity_journal_id=None,
                        activity_group_name=None, activity_group_id=None, with_timespan=False,
                        quiet=False):

    if bookmarks:
        if start or finish or local_time or time or activity_journal_id:
            raise Exception('Cannot use bookmarks with additional activity constraints')
        return pd.concat(_activity_statistics(s, *statistics, owner=owner, constraint=constraint,
                                              start=bookmark.start, finish=bookmark.finish,
                                              activity_journal_id=bookmark.activity_journal_id,
                                              activity_group_name=activity_group_name,
                                              activity_group_id=activity_group_id, with_timespan=with_timespan,
                                              quiet=quiet)
                         for bookmark in bookmarks)
    else:
        return _activity_statistics(s, *statistics, owner=owner, constraint=constraint, start=start, finish=finish,
                                    local_time=local_time, time=time, activity_journal_id=activity_journal_id,
                                    activity_group_name=activity_group_name, activity_group_id=activity_group_id,
                                    with_timespan=with_timespan, quiet=quiet)


def _activity_statistics(s, *statistics, owner=None, constraint=None, start=None, finish=None,
                         local_time=None, time=None, activity_journal_id=None,
                         activity_group_name=None, activity_group_id=None, with_timespan=False,
                         quiet=False):

    statistic_names, statistic_ids = _collect_statistics(s, statistics, owner=owner, constraint=constraint)
    log.debug('Statistics IDs %s' % statistic_ids)
    activity_journal_id = resolve_activity(s, local_time=local_time, time=time,
                                           activity_journal_id=activity_journal_id,
                                           activity_group_name=activity_group_name,
                                           activity_group_id=activity_group_id)

    t = _tables()
    q = select([t.sn.c.name, t.sj.c.time, coalesce(t.sjf.c.value, t.sji.c.value, t.sjt.c.value), t.at.c.id]). \
        select_from(t.sj.join(t.sn).outerjoin(t.sjf).outerjoin(t.sji).outerjoin(t.sjt)). \
        where(and_(t.sn.c.id.in_(statistic_ids), t.sj.c.source_id == activity_journal_id)). \
        select_from(t.at). \
        where(and_(t.at.c.start <= t.sj.c.time, t.at.c.finish >= t.sj.c.time,
                   t.at.c.activity_journal_id == activity_journal_id)). \
        order_by(t.sj.c.time)
    if start:
        q = q.where(t.sj.c.time >= start)
    if finish:
        q = q.where(t.sj.c.time < finish)
    log.debug(q)

    data, times = defaultdict(list), []
    pad = make_pad(data, times, statistic_names, quiet=quiet)

    for name, time, value, timespan in s.connection().execute(q):
        if times and times[-1] != time:
            pad()
        if not times or times[-1] != time:
            times.append(time)
            if with_timespan:
                data[TIMESPAN_ID].append(timespan)
        if len(data[name]) >= len(times):
            raise Exception('Duplicate data for %s at %s ' % (name, time) +
                            '(you may need to specify more constraints to make the query unique)')
        data[name].append(value)
    pad()

    return pd.DataFrame(data, index=times)


def statistic_quartiles(s, *statistics, start=None, finish=None, owner=None, constraint=None, source_ids=None,
                        schedule=None):

    statistic_names, statistic_ids = _collect_statistics(s, statistics, owner, constraint)
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
    if source_ids is not None:
        q = q.filter(StatisticJournal.source_id.in_(source_ids))
    if schedule:
        q = q.join((Interval, StatisticMeasure.source_id == Interval.id)). \
            filter(Interval.schedule == schedule)
    log.debug(q)

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


MIN_PERIODS = 1

def std_activity_statistics(s, local_time=None, time=None, activity_journal_id=None,
                            activity_group_name=None, activity_group_id=None):

    stats = activity_statistics(s, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE,
                                ELEVATION, SPEED, HR_ZONE, HR_IMPULSE_10, ALTITUDE, CADENCE, POWER,
                                local_time=local_time, time=time, activity_journal_id=activity_journal_id,
                                activity_group_name=activity_group_name, activity_group_id=activity_group_id,
                                with_timespan=True)

    stats[DISTANCE_KM] = stats[DISTANCE]/1000
    stats[SPEED_KMH] = stats[SPEED] * 3.6
    stats[MED_SPEED_KMH] = stats[SPEED].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median() * 3.6
    stats[MED_HR_IMPULSE_10] = stats[HR_IMPULSE_10].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median()
    stats[MED_CADENCE] = stats[CADENCE].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median()
    if POWER in stats.columns:
        stats[MED_POWER_W] = stats[POWER].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median().clip(lower=0)
    stats.rename(columns={ELEVATION: ELEVATION_M}, inplace=True)

    stats['keep'] = pd.notna(stats[HR_IMPULSE_10])
    stats.interpolate(method='time', inplace=True)
    stats = stats.loc[stats['keep'] == True]

    stats[CLIMB_MS] = stats[ELEVATION_M].diff() * 0.1
    stats[TIME] = pd.to_datetime(stats.index)
    stats[LOCAL_TIME] = stats[TIME].apply(lambda x: time_to_local_time(x.to_pydatetime(), HMS))

    return stats


def std_health_statistics(s, start=None, finish=None):

    from ..stoats.calculate.monitor import MonitorCalculator

    # this assumes FF cover all the dates and HR/steps fit into them.  may not be true in all cases?
    # also, we downsample the FF data to hourly intervals then shift daily data to match one of those times
    # this avoids introducing gaps in the FF data when merging that mess up the continuity of the plots.
    stats_1 = statistics(s, FITNESS, FATIGUE, start=start, finish=finish).resample('1h').mean()
    stats_2 = statistics(s, REST_HR, start=start, finish=finish, owner=MonitorCalculator). \
        reindex(stats_1.index, method='nearest', tolerance=dt.timedelta(minutes=30))
    stats_3 = statistics(s, DAILY_STEPS, ACTIVE_TIME, ACTIVE_DISTANCE, start=start, finish=finish). \
        reindex(stats_1.index, method='nearest', tolerance=dt.timedelta(minutes=30))
    stats = stats_1.merge(stats_2, how='outer', left_index=True, right_index=True)
    stats = stats.merge(stats_3, how='outer', left_index=True, right_index=True)
    stats[LOG_FITNESS] = np.log10(stats[FITNESS])
    stats[LOG_FATIGUE] = np.log10(stats[FATIGUE])
    stats[ACTIVE_TIME_H] = stats[ACTIVE_TIME] / 3600
    stats[ACTIVE_DISTANCE_KM] = stats[ACTIVE_DISTANCE] / 1000
    stats[TIME] = pd.to_datetime(stats.index)
    stats[LOCAL_TIME] = stats[TIME].apply(lambda x: time_to_local_time(x.to_pydatetime(), YMD))

    return stats


def nearby_activities(s, local_time=None, time=None, activity_journal_id=None,
                      activity_group_name=None, activity_group_id=None):
    activity_journal_id = resolve_activity(s, local_time, time, activity_journal_id,
                                           activity_group_name=activity_group_name,
                                           activity_group_id=activity_group_id)
    return nearby_any_time(s, ActivityJournal.from_id(s, activity_journal_id))


def bookmarks(s, constraint, owner=CoastingBookmark):
    yield from s.query(ActivityBookmark). \
        filter(ActivityBookmark.owner == owner,
               ActivityBookmark.constraint == constraint).all()


def statistic_names(s, *statistics, owner=None, constraint=None):
    q = s.query(StatisticName). \
        filter(or_(StatisticName.name.like(statistic) for statistic in statistics))
    if owner:
        q = q.filter(StatisticName.owner == owner)
    if constraint:
        q = q.filter(StatisticName.constraint == constraint)
    return q.all()


def _type_to_journal(t):
    return {StatisticJournalType.INTEGER: t.sji,
            StatisticJournalType.FLOAT: t.sjf,
            StatisticJournalType.TEXT: t.sjt}


def statistics(s, *statistics, start=None, finish=None, owner=None, constraint=None):
    # todo - rather than adding more constraints here, make it possible to pass in statistic_name instances
    t = _tables()
    ttj = _type_to_journal(t)
    names = statistic_names(s, *statistics, owner=owner, constraint=constraint)
    counts = Counter(name.name for name in names)
    labels = [name.name if counts[name.name] == 1 else f'{name.name} ({name.constraint})' for name in names]
    tables = [ttj[name.statistic_journal_type] for name in names]
    time_select = select([distinct(t.sj.c.time).label("time")]).select_from(t.sj). \
        where(t.sj.c.statistic_name_id.in_([n.id for n in names]))
    if start:
        time_select = time_select.where(t.sj.c.time >= start)
    if finish:
        time_select = time_select.where(t.sj.c.time <= finish)
    time_select = time_select.order_by("time").alias("sub_time")  # order here avoids extra index
    sub_selects = [select([table.c.value, t.sj.c.time]).
                       select_from(t.sj.join(table)).
                       where(t.sj.c.statistic_name_id == name.id).
                       order_by(t.sj.c.time).  # this doesn't affect plan but seems to speed up query
                       alias(f'sub_{name.name}_{name.constraint}')
                   for name, table in zip(names, tables)]
    # don't call this TIME because even though it's moved to index it somehow blocks the later additiion
    # of a TIME column (eg when plotting health statistics)
    selects = [time_select.c.time.label(INDEX)] + \
              [sub.c.value.label(label) for sub, label in zip(sub_selects, labels)]
    sources = time_select
    for sub in sub_selects:
        sources = sources.outerjoin(sub, time_select.c.time == sub.c.time)
    sql = select(selects).select_from(sources)
    return pd.read_sql_query(sql=sql, con=s.connection(), index_col=INDEX)


def present(df, *names):
    return all(name in df.columns and len(df[name]) for name in names)
