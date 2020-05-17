
import datetime as dt
from collections import Counter
from logging import getLogger
from re import compile

import numpy as np
import pandas as pd
from sqlalchemy import inspect, select, and_, or_, distinct
from sqlalchemy.orm.exc import NoResultFound

from .coasting import CoastingBookmark
from ..lib.data import kargs_to_attr
from ..lib.date import local_time_to_time, local_date_to_time
from ..names import Names as N, like
from ..sql import StatisticName, StatisticJournal, StatisticJournalInteger, ActivityJournal, \
    StatisticJournalFloat, StatisticJournalText, Interval, Source
from ..sql.database import connect, ActivityTimespan, ActivityGroup, ActivityBookmark, StatisticJournalType, \
    Composite, CompositeComponent, ActivityNearby

log = getLogger(__name__)


# in general these functions should (or are being written to) take both ORM objects and parameters
# to retrieve those objects if missing.  so, for example, activity_statistics can be called with
# StatisticName and ActivityJournal instances, or it can be called with more low-level parameters.
# the low-level parameters are often useful interactively but make simplifying assumptions; the ORM
# instances give complete control.


def df(query):
    # https://stackoverflow.com/questions/29525808/sqlalchemy-orm-conversion-to-pandas-dataframe
    return pd.read_sql(query.statement, query.session.bind)


def session(*args):
    ns, db = connect(args)
    return db.session()


def _tables():
    return kargs_to_attr(sj=inspect(StatisticJournal).local_table,
                         sn=inspect(StatisticName).local_table,
                         sji=inspect(StatisticJournalInteger).local_table,
                         sjf=inspect(StatisticJournalFloat).local_table,
                         sjt=inspect(StatisticJournalText).local_table,
                         inv=inspect(Interval).local_table,
                         at=inspect(ActivityTimespan).local_table,
                         aj=inspect(ActivityJournal).local_table,
                         cmp=inspect(Composite).local_table,
                         cc=inspect(CompositeComponent).local_table,
                         src=inspect(Source).local_table)


def activity_journal(s, activity_journal=None, local_time=None, time=None, activity_group=None):
    if activity_journal:
        if local_time or time or activity_group:
            raise Exception('Activity Journal given, so extra activity-related parameters are unused')
    else:
        if local_time:
            time = local_time_to_time(local_time)
        if not time:
            raise Exception('Specify activity_journal or time')
        try:
            # first, if an activity includes that time
            q = s.query(ActivityJournal). \
                filter(ActivityJournal.start <= time,
                       ActivityJournal.finish >= time)
            if activity_group:
                q = q.filter(ActivityJournal.activity_group == ActivityGroup.from_name(s, activity_group))
            activity_journal = q.one()
        except NoResultFound:
            # second, if anything in the following 24 hours (eg if just date given)
            q = s.query(ActivityJournal). \
                filter(ActivityJournal.start > time,
                       ActivityJournal.finish < time + dt.timedelta(days=1))
            if activity_group:
                q = q.filter(ActivityJournal.activity_group == ActivityGroup.from_name(s, activity_group))
            activity_journal = q.one()
        log.info(f'Using Activity Journal {activity_journal}')
    return activity_journal

_activity_journal = activity_journal


def _add_bookmark(bookmark, df):
    df[N.BOOKMARK] = bookmark.id
    return df


def activity_statistics(s, *statistics, start=None, finish=None, owners=None,
                        local_time=None, time=None, bookmarks=None, activity_journal=None,
                        activity_group=None, with_timespan=False, check=True):

    if bookmarks:
        if start or finish or local_time or time or activity_journal or activity_group:
            raise Exception('Cannot use bookmarks with additional activity constraints')
        return pd.concat(_add_bookmark(bookmark,
                                       _activity_statistics(s, *statistics, owners=owners,
                                                            start=bookmark.start, finish=bookmark.finish,
                                                            activity_journal=bookmark.activity_journal,
                                                            with_timespan=with_timespan, check=check))
                         for bookmark in bookmarks)
    else:
        return _activity_statistics(s, *statistics, owners=owners, start=start, finish=finish,
                                    local_time=local_time, time=time, activity_journal=activity_journal,
                                    activity_group=activity_group, with_timespan=with_timespan, check=check)


def _activity_statistics(s, *statistics, owners=None, start=None, finish=None,
                         local_time=None, time=None, activity_journal=None,
                         activity_group=None, with_timespan=False, check=True):

    activity_journal = _activity_journal(s, activity_journal=activity_journal, local_time=local_time,
                                         time=time, activity_group=activity_group)
    if activity_group is None:
        activity_group = activity_journal.activity_group
    names = statistic_names(s, *statistics, owners=owners, activity_group=activity_group, check=check)
    counts = Counter(name.name for name in names)

    t = _tables()
    ttj = _type_to_journal(t)
    labels = [name.name if counts[name.name] == 1 else f'{name.name}:{name.activity_group}:{name.owner}' for name in names]
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
                       copy(f'sub_{name.name}_{name.activity_group}_{name.owner}')
                   for name, table in zip(names, tables)]
    # don't call this TIME because even though it's moved to index it somehow blocks the later addition
    # of a TIME column (eg when plotting health statistics)
    selects = [time_select.c.time.label(N.INDEX)] + \
              [sub.c.value.label(label) for sub, label in zip(sub_selects, labels)]
    sources = time_select
    for sub in sub_selects:
        sources = sources.outerjoin(sub, time_select.c.time == sub.c.time)
    if with_timespan:
        selects += [t.at.c.id.label(N.TIMESPAN_ID)]
        sources = sources.outerjoin(t.at,
                                    and_(t.at.c.start <= time_select.c.time,
                                         t.at.c.finish > time_select.c.time,
                                         t.at.c.activity_journal_id == activity_journal.id))
    sql = select(selects).select_from(sources)
    # log.debug(sql)
    return pd.read_sql_query(sql=sql, con=s.connection(), index_col=N.INDEX)


def nearby_activities(s, local_time=None, time=None, activity_group=None):
    from ..pipeline.display.activity.nearby import nearby_any_time
    activity_journal = _activity_journal(s, local_time=local_time, time=time,
                                         activity_group=activity_group)
    return nearby_any_time(s, activity_journal)


def bookmarks(s, constraint, owner=CoastingBookmark):
    yield from s.query(ActivityBookmark). \
        filter(ActivityBookmark.owner == owner,
               ActivityBookmark.constraint == constraint).all()


def statistic_names(s, *statistics, owners=tuple(), activity_group=None, check=True):
    unresolved = [statistic for statistic in statistics if not isinstance(statistic, StatisticName)]
    if unresolved:
        q = s.query(StatisticName). \
            filter(or_(StatisticName.name.like(statistic) for statistic in unresolved))
        if owners:
            q = q.filter(StatisticName.owner.in_(owners))
        if activity_group:
            q = q.filter(StatisticName.activity_group == ActivityGroup.from_name(s, activity_group))
        resolved = q.all()
    else:
        resolved = []
    some = [statistic for statistic in statistics if isinstance(statistic, StatisticName)] + resolved
    if check and not some:
        raise Exception(f'Found no statistics for {statistics} (owners {owners}; activity group {activity_group})')
    return some


def _type_to_journal(t):
    return {StatisticJournalType.INTEGER: t.sji,
            StatisticJournalType.FLOAT: t.sjf,
            StatisticJournalType.TEXT: t.sjt}


def statistics(s, *statistics, start=None, finish=None, local_start=None, local_finish=None,
               owners=tuple(), activity_group=None, sources=None, with_sources=False, check=True):
    t = _tables()
    ttj = _type_to_journal(t)
    names = statistic_names(s, *statistics, owners=owners, activity_group=activity_group, check=check)
    counts = Counter(name.name for name in names)
    labels = [name.name if counts[name.name] == 1 else f'{name.name}:{name.activity_group}' for name in names]
    tables = [ttj[name.statistic_journal_type] for name in names]
    if local_start:
        if start: raise Exception('Provide only one of start, local_start')
        start = local_date_to_time(local_start)
    if local_finish:
        if finish: raise Exception('Provide only one of finish, local_finish')
        finish = local_date_to_time(local_finish)
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
        return q.order_by(t.sj.c.time).alias(f'sub_{name.name}_{name.activity_group}')

    sub_selects = [sub_select(name, table) for name, table in zip(names, tables)]
    # don't call this TIME because even though it's moved to index it somehow blocks the later addition
    # of a TIME column (eg when plotting health statistics)
    selects = [time_select.c.time.label(N.INDEX)] + \
              [sub.c.value.label(label) for sub, label in zip(sub_selects, labels)]
    if with_sources:
        selects += [sub.c.source_id.label(N._src(label)) for sub, label in zip(sub_selects, labels)]
    sources = time_select
    for sub in sub_selects:
        sources = sources.outerjoin(sub, time_select.c.time == sub.c.time)
    sql = select(selects).select_from(sources)
    return pd.read_sql_query(sql=sql, con=s.connection(), index_col=N.INDEX)


def present(df, *names, pattern=False):
    if pattern:
        if hasattr(df, 'columns'):
            for name in names:
                columns = like(name, df.columns)
                if not columns or not all(len(df[column].dropna()) for column in columns):
                    return False
            return True
        else:
            return df is not None and (len(df.dropna()) and all(like(name, [df.name]) for name in names))
    else:
        if hasattr(df, 'columns'):
            return all(name in df.columns and len(df[name].dropna()) for name in names)
        else:
            return df is not None and (len(df.dropna()) and all(df.name == name for name in names))


def median_d(df):
    return pd.Series(df.index).diff().median()


KEEP = 'keep'


def linear_resample(df, start=None, finish=None, d=None, quantise=True):
    log.debug(f'Linear resample with index {type(df.index)}, columns {df.columns}')
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


def linear_resample_time(df, start=None, finish=None, dt=None, with_timespan=False, keep_nan=True, add_time=True):
    log.debug(f'Linear resample with index {type(df.index)}, columns {df.columns}')
    if with_timespan is None: with_timespan = N.TIMESPAN_ID in df.columns
    dt = dt or median_dt(df)
    start = start or df.index.min()
    finish = finish or df.index.max()
    lin = pd.DataFrame({KEEP: True}, index=pd.date_range(start=start, end=finish, freq=f'{dt}S'))
    ldf = df.join(lin, how='outer', sort=True)
    # if this fails check for time-like columns
    ldf.interpolate(method='index', limit_area='inside', inplace=True)
    ldf = ldf.loc[ldf[KEEP] == True].drop(columns=[KEEP])
    if add_time:
        ldf[N.TIME] = ldf.index
        ldf[N.DELTA_TIME] = ldf[N.TIME].diff()
    if with_timespan:
        if keep_nan:
            ldf.loc[~ldf[N.TIMESPAN_ID].isin(df[N.TIMESPAN_ID].unique())] = np.nan
        else:
            ldf = ldf.loc[ldf[N.TIMESPAN_ID].isin(df[N.TIMESPAN_ID].unique())]
    return ldf


def groups_by_time(s, start=None, finish=None):
    q = s.query(ActivityJournal.start.label(N.INDEX), ActivityNearby.group.label(N.GROUP)). \
        filter(ActivityNearby.activity_journal_id == ActivityJournal.id)
    if start:
        q = q.filter(ActivityJournal.start >= start)
    if finish:
        q = q.filter(ActivityJournal.start < finish)
    return pd.read_sql_query(sql=q.statement, con=s.connection(), index_col=N.INDEX)


def coallesce(df, *statistics, activity_group_label=None, mixed=N.MIXED,
              unpack=r'({statistic})\s*:\s*([^:]+)', pack='{statistic}:{activity_group}'):
    '''
    Combine statistics with more than one constraint.

    When multiple statistics with the same name are requested, they are distinguished by their
    activity_group.  So if you request 'Active Time' for multiple groups you will get
    'active_time:ride' etc.

    This function combines these into a single column (in the example, 'Active Time'), while also optionally
    extracting the constraint into a separate column.

    If two values occur at the same time they are added together.  The label is then changed to MIXED.
    '''
    for statistic in statistics:
        if activity_group_label and activity_group_label not in df.columns:
            df[activity_group_label] = np.nan
        for full_statistic, activity_group in related_statistics(df, statistic, unpack=unpack):
            if full_statistic not in df.columns:
                df[full_statistic] = np.nan
            column = pack.format(statistic=full_statistic, activity_group=activity_group)
            if activity_group_label:
                df.loc[~df[column].isna() & ~df[activity_group_label].isna() & ~(df[activity_group_label] == activity_group),
                       activity_group_label] = mixed
                df.loc[~df[column].isna() & df[activity_group_label].isna(), activity_group_label] = activity_group
            df.loc[~df[full_statistic].isna() & ~df[column].isna(), full_statistic] += \
                df.loc[~df[full_statistic].isna() & ~df[column].isna(), column]
            df.loc[df[full_statistic].isna() & ~df[column].isna(), full_statistic] = \
                df.loc[df[full_statistic].isna() & ~df[column].isna(), column]
    return df


def coallesce_like(df, *statistics):
    return coallesce(df, *statistics, unpack=r'({statistic}.*?)\s*:\s*([^:]+)')


def related_statistics(df, statistic, unpack=r'({statistic})\s*:\s*([^:]+)'):
    rx = compile(unpack.format(statistic=statistic))
    for column in df.columns:
        m = rx.match(column)
        if m: yield m.group(1), m.group(2)


def transform(df, transformation):
    transformation = {key: value for key, value in transformation.items() if key in df.columns}
    return df.transform(transformation)


def drop_empty(df):
    for column in df.columns:
        if df[column].dropna().empty:
            df = df.drop(columns=[column])
    return df
