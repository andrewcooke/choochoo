from logging import getLogger

import numpy as np
import pandas as pd
from sqlalchemy import inspect

from .coasting import CoastingBookmark
from ..lib.data import kargs_to_attr
from ..names import Names as N, like
from ..sql import StatisticName, StatisticJournal, StatisticJournalInteger, ActivityJournal, \
    StatisticJournalFloat, StatisticJournalText, Interval, Source
from ..sql.database import connect, ActivityTimespan, ActivityBookmark, Composite, \
    CompositeComponent, ActivityNearby

log = getLogger(__name__)



def read_query(query, index=None):
    '''
    Convert s.query(OrmClass) to a dataframe
    https://stackoverflow.com/questions/29525808/sqlalchemy-orm-conversion-to-pandas-dataframe
    '''
    return pd.read_sql(query.statement, query.session.bind, index_col=index)


def session(*args):
    '''
    Create a database session (used in Jupyter templates)
    '''
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


def nearby_activities(s, local_time=None, activity_group=None):
    from ..pipeline.display.activity.nearby import nearby_any_time
    journal = ActivityJournal.at_local_time(s, local_time, activity_group=activity_group)
    return nearby_any_time(s, journal)


def bookmarks(s, constraint, owner=CoastingBookmark):
    yield from s.query(ActivityBookmark). \
        filter(ActivityBookmark.owner == owner,
               ActivityBookmark.constraint == constraint).all()


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
    return read_query(q, index=N.INDEX)


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
