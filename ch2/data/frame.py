
import datetime as dt
from collections import defaultdict, Counter
from collections.abc import Mapping, Sequence
from logging import getLogger

import numpy as np
import pandas as pd
from sqlalchemy import inspect, select, and_, or_, distinct
from sqlalchemy.sql.functions import coalesce

from ch2.stoats.names import DELTA_TIME, HEART_RATE, _src, FITNESS_D_ANY, FATIGUE_D_ANY, like, _log
from ..lib.data import kargs_to_attr
from ..lib.date import local_time_to_time, time_to_local_time, YMD, HMS
from ..squeal import StatisticName, StatisticJournal, StatisticJournalInteger, ActivityJournal, \
    StatisticJournalFloat, StatisticJournalText, Interval, StatisticMeasure, Source
from ..squeal.database import connect, ActivityTimespan, ActivityGroup, ActivityBookmark, StatisticJournalType, \
    Composite, CompositeComponent
from ..stoats.display.nearby import nearby_any_time
from ..stoats.names import DISTANCE_KM, SPEED_KMH, MED_SPEED_KMH, MED_HR_IMPULSE_10, MED_CADENCE, \
    ELEVATION_M, CLIMB_MS, ACTIVE_TIME_H, ACTIVE_DISTANCE_KM, MED_POWER_ESTIMATE_W, \
    TIMESPAN_ID, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE, MED_WINDOW, \
    ELEVATION, SPEED, HR_ZONE, HR_IMPULSE_10, ALTITUDE, CADENCE, TIME, LOCAL_TIME, REST_HR, \
    DAILY_STEPS, ACTIVE_TIME, ACTIVE_DISTANCE, POWER_ESTIMATE, INDEX
from ch2.data.coasting import CoastingBookmark

log = getLogger(__name__)


# in general these functions should (or are being written to) take both ORM objects and parameters
# to retrieve those objects if missing.  so, for example, activity_statistics can be called with
# StatisticName and ActivityJournal instances, or it can be called with more low-level parameters.
# the low-level parameters are often useful interactively but make simplifying asumptions; the ORM
# instances give complete control.


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


def activity_journal(s, activity_journal=None, local_time=None, time=None, activity_group_name=None):
    '''
    If activity_journal_id is given, it is returned.

    Otherwise, specify one of (local_time, time) and one of (activity_group_name, activity_group_id).
    '''

    if activity_journal:
        if local_time or time or activity_group_name:
            raise Exception('Activity Journal given, so extra activity-related parameters are unused')
    else:
        if local_time:
            time = local_time_to_time(local_time)
        if not time or not activity_group_name:
            raise Exception('Specify activity_journal or time and activity_group_name')
        activity_journal = s.query(ActivityJournal). \
            join(ActivityGroup). \
            filter(ActivityJournal.start <= time,
                   ActivityJournal.finish >= time,
                   ActivityGroup.name == activity_group_name).one()
        log.info(f'Using Activity Journal {activity_journal}')
    return activity_journal

_activity_journal = activity_journal


def activity_statistics(s, *statistics, owner=None, constraint=None, start=None, finish=None,
                        local_time=None, time=None, bookmarks=None, activity_journal=None,
                        activity_group_name=None, with_timespan=False):

    if bookmarks:
        if start or finish or local_time or time or activity_journal or activity_group_name:
            raise Exception('Cannot use bookmarks with additional activity constraints')
        return pd.concat(_activity_statistics(s, *statistics, owner=owner, constraint=constraint,
                                              start=bookmark.start, finish=bookmark.finish,
                                              activity_journal=bookmark.activity_journal,
                                              with_timespan=with_timespan)
                         for bookmark in bookmarks)
    else:
        return _activity_statistics(s, *statistics, owner=owner, constraint=constraint, start=start, finish=finish,
                                    local_time=local_time, time=time, activity_journal=activity_journal,
                                    activity_group_name=activity_group_name, with_timespan=with_timespan)


def _activity_statistics(s, *statistics, owner=None, constraint=None, start=None, finish=None,
                         local_time=None, time=None, activity_journal=None,
                         activity_group_name=None, with_timespan=False):

    activity_journal = _activity_journal(s, activity_journal=activity_journal, local_time=local_time,
                                         time=time, activity_group_name=activity_group_name)
    if constraint is None:
        constraint = activity_journal.activity_group
    names = _statistic_names(s, *statistics, owner=owner, constraint=constraint)
    counts = Counter(name.name for name in names)

    t = _tables()
    ttj = _type_to_journal(t)
    labels = [name.name if counts[name.name] == 1 else f'{name.name} ({name.constraint})' for name in names]
    tables = [ttj[name.statistic_journal_type] for name in names]
    time_select = select([distinct(t.sj.c.time).label("time")]).select_from(t.sj). \
        where(and_(t.sj.c.statistic_name_id.in_([n.id for n in names]),
                   t.sj.c.source_id == activity_journal.id))
    if start:
        time_select = time_select.where(t.sj.c.time >= start)
    if finish:
        time_select = time_select.where(t.sj.c.time <= finish)
    time_select = time_select.order_by("time").alias("sub_time")  # order here avoids extra index
    sub_selects = [select([table.c.value, t.sj.c.time]).
                       select_from(t.sj.join(table)).
                       where(and_(t.sj.c.statistic_name_id == name.id,
                                  t.sj.c.source_id == activity_journal.id)).
                       order_by(t.sj.c.time).  # this doesn't affect plan but seems to speed up query
                       alias(f'sub_{name.name}_{name.constraint}')
                   for name, table in zip(names, tables)]
    # don't call this TIME because even though it's moved to index it somehow blocks the later addition
    # of a TIME column (eg when plotting health statistics)
    selects = [time_select.c.time.label(INDEX)] + \
              [sub.c.value.label(label) for sub, label in zip(sub_selects, labels)]
    sources = time_select
    for sub in sub_selects:
        sources = sources.outerjoin(sub, time_select.c.time == sub.c.time)
    if with_timespan:
        selects += [t.at.c.id.label(TIMESPAN_ID)]
        sources = sources.outerjoin(t.at,
                                    and_(t.at.c.start <= time_select.c.time,
                                         t.at.c.finish > time_select.c.time,
                                         t.at.c.activity_journal_id == activity_journal.id))
    sql = select(selects).select_from(sources)
    return pd.read_sql_query(sql=sql, con=s.connection(), index_col=INDEX)


def statistic_quartiles(s, *statistics, start=None, finish=None, owner=None, constraint=None, source_ids=None,
                        schedule=None):

    # todo - rewrite using new approach

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

def std_activity_statistics(s, local_time=None, time=None, activity_journal=None, activity_group_name=None,
                            with_timespan=True):

    stats = activity_statistics(s, LATITUDE, LONGITUDE, SPHERICAL_MERCATOR_X, SPHERICAL_MERCATOR_Y, DISTANCE,
                                ELEVATION, SPEED, HEART_RATE, HR_ZONE, HR_IMPULSE_10, ALTITUDE, CADENCE,
                                POWER_ESTIMATE,
                                local_time=local_time, time=time, activity_journal=activity_journal,
                                activity_group_name=activity_group_name, with_timespan=with_timespan)

    stats[DISTANCE_KM] = stats[DISTANCE]/1000
    stats[SPEED_KMH] = stats[SPEED] * 3.6
    stats[MED_SPEED_KMH] = stats[SPEED].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median() * 3.6
    stats[MED_HR_IMPULSE_10] = stats[HR_IMPULSE_10].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median()
    stats[MED_CADENCE] = stats[CADENCE].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median()
    if POWER_ESTIMATE in stats.columns:
        stats[MED_POWER_ESTIMATE_W] = stats[POWER_ESTIMATE].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median().clip(lower=0)
    stats.rename(columns={ELEVATION: ELEVATION_M}, inplace=True)

    if with_timespan:
        timespans = stats[TIMESPAN_ID].unique()
    stats['keep'] = pd.notna(stats[HR_IMPULSE_10])
    stats.interpolate(method='time', inplace=True)
    stats = stats.loc[stats['keep'] == True].drop(columns=['keep'])
    if with_timespan:
        stats = stats.loc[stats[TIMESPAN_ID].isin(timespans)]

    stats[CLIMB_MS] = stats[ELEVATION_M].diff() * 0.1
    stats[TIME] = pd.to_datetime(stats.index)
    stats[LOCAL_TIME] = stats[TIME].apply(lambda x: time_to_local_time(x.to_pydatetime(), HMS))

    return stats


def std_health_statistics(s, *extra, start=None, finish=None):

    from ..stoats.calculate.monitor import MonitorCalculator

    # this assumes FF cover all the dates and HR/steps fit into them.  may not be true in all cases?
    # also, we downsample the FF data to hourly intervals then shift daily data to match one of those times
    # this avoids introducing gaps in the FF data when merging that mess up the continuity of the plots.
    stats_1 = statistics(s, FITNESS_D_ANY, FATIGUE_D_ANY, start=start, finish=finish).resample('1h').mean()
    stats_2 = statistics(s, REST_HR, start=start, finish=finish, owner=MonitorCalculator). \
        reindex(stats_1.index, method='nearest', tolerance=dt.timedelta(minutes=30))
    stats_3 = statistics(s, DAILY_STEPS, ACTIVE_TIME, ACTIVE_DISTANCE, *extra, start=start, finish=finish). \
        reindex(stats_1.index, method='nearest', tolerance=dt.timedelta(minutes=30))
    stats = stats_1.merge(stats_2, how='outer', left_index=True, right_index=True)
    stats = stats.merge(stats_3, how='outer', left_index=True, right_index=True)
    for fitness in like(FITNESS_D_ANY, stats.columns):
        stats[_log(fitness)] = np.log10(stats[fitness])
    for fatigue in like(FATIGUE_D_ANY, stats.columns):
        stats[_log(fatigue)] = np.log10(stats[fatigue])
    stats[ACTIVE_TIME_H] = stats[ACTIVE_TIME] / 3600
    stats[ACTIVE_DISTANCE_KM] = stats[ACTIVE_DISTANCE] / 1000
    stats[TIME] = pd.to_datetime(stats.index)
    stats[LOCAL_TIME] = stats[TIME].apply(lambda x: time_to_local_time(x.to_pydatetime(), YMD))

    return stats


def nearby_activities(s, local_time=None, time=None, activity_journal_id=None, activity_group_name=None):
    activity_journal_id = activity_journal(s, local_time, time, activity_journal_id,
                                           activity_group_name=activity_group_name)
    return nearby_any_time(s, ActivityJournal.from_id(s, activity_journal_id))


def bookmarks(s, constraint, owner=CoastingBookmark):
    yield from s.query(ActivityBookmark). \
        filter(ActivityBookmark.owner == owner,
               ActivityBookmark.constraint == constraint).all()


def statistic_names(s, *statistics, owner=None, constraint=None):
    unresolved = [statistic for statistic in statistics if not isinstance(statistic, StatisticName)]
    if unresolved:
        q = s.query(StatisticName). \
            filter(or_(StatisticName.name.like(statistic) for statistic in unresolved))
        if owner:
            q = q.filter(StatisticName.owner == owner)
        if constraint:
            q = q.filter(StatisticName.constraint == constraint)
        resolved = q.all()
    else:
        resolved = []
    return [statistic for statistic in statistics if isinstance(statistic, StatisticName)] + resolved

_statistic_names = statistic_names


def _type_to_journal(t):
    return {StatisticJournalType.INTEGER: t.sji,
            StatisticJournalType.FLOAT: t.sjf,
            StatisticJournalType.TEXT: t.sjt}


def statistics(s, *statistics, start=None, finish=None, owner=None, constraint=None, sources=None,
               with_sources=False):
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

    def sub_select(name, table):
        selects = [table.c.value, t.sj.c.time]
        if with_sources:
            selects += [t.sj.c.source_id]
        q = select(selects). \
                   select_from(t.sj.join(table)). \
                   where(t.sj.c.statistic_name_id == name.id)
        if sources:
            q = q.where(t.sj.c.source_id.in_(source.id for source in sources))
        # order_by doesn't affect plan but seems to speed up query
        return q.order_by(t.sj.c.time).alias(f'sub_{name.name}_{name.constraint}')

    sub_selects = [sub_select(name, table) for name, table in zip(names, tables)]
    # don't call this TIME because even though it's moved to index it somehow blocks the later addition
    # of a TIME column (eg when plotting health statistics)
    selects = [time_select.c.time.label(INDEX)] + \
              [sub.c.value.label(label) for sub, label in zip(sub_selects, labels)]
    if with_sources:
        selects += [sub.c.source_id.label(_src(label)) for sub, label in zip(sub_selects, labels)]
    sources = time_select
    for sub in sub_selects:
        sources = sources.outerjoin(sub, time_select.c.time == sub.c.time)
    sql = select(selects).select_from(sources)
    return pd.read_sql_query(sql=sql, con=s.connection(), index_col=INDEX)


def present(df, *names):
    if hasattr(df, 'columns'):
        return df is not None and all(name in df.columns and len(df[name].dropna()) for name in names)
    else:
        return df is not None and (len(df.dropna()) and all(df.name == name for name in names))


def median_d(df):
    return pd.Series(df.index).diff().median()


KEEP = 'keep'


def linear_resample(df, start=None, finish=None, d=None, quantise=True):
    log.debug(f'Linear resample with type {type(df.index)}, columns {df.columns}')
    d = d or median_d(df)
    start = start or df.index.min()
    finish = finish or df.index.max()
    if quantise:
        start, finish = int(start / d) * d, (1 + int(finish / d)) * d
    lin = pd.DataFrame({KEEP: True}, index=np.arange(start, finish, d))
    ldf = df.join(lin, how='outer', sort=True)
    # if this fails check for time-like columns
    ldf.interpolate(method='slinear', limit_area='inside', inplace=True)
    ldf = ldf.loc[ldf[KEEP] == True].drop(columns=[KEEP])
    return ldf


def median_dt(df):
    return pd.Series(df.index).diff().median().total_seconds()


def linear_resample_time(df, start=None, finish=None, dt=None, with_timespan=None, keep_nan=True, add_time=True):
    log.debug(f'Linear resample with type {type(df.index)}, columns {df.columns}')
    if with_timespan is None: with_timespan = TIMESPAN_ID in df.columns
    dt = dt or median_dt(df)
    start = start or df.index.min()
    finish = finish or df.index.max()
    lin = pd.DataFrame({KEEP: True}, index=pd.date_range(start=start, end=finish, freq=f'{dt}S'))
    ldf = df.copy().join(lin, how='outer', sort=True)
    # if this fails check for time-like columns
    ldf.interpolate(method='index', limit_area='inside', inplace=True)
    ldf = ldf.loc[ldf[KEEP] == True].drop(columns=[KEEP])
    if add_time:
        ldf[TIME] = ldf.index
        ldf[DELTA_TIME] = ldf[TIME].diff()
    if with_timespan:
        if keep_nan:
            ldf.loc[~ldf[TIMESPAN_ID].isin(df[TIMESPAN_ID].unique())] = np.nan
        else:
            ldf = ldf.loc[ldf[TIMESPAN_ID].isin(df[TIMESPAN_ID].unique())]
    return ldf
