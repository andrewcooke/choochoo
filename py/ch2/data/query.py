
from logging import getLogger

import numpy as np
import pandas as pd
from sqlalchemy import asc, desc, distinct
from sqlalchemy.orm import aliased

from ..data import session, present
from ..lib import local_date_to_time, to_date, time_to_local_time
from ..lib.date import YMD
from ..lib.log import log_current_exception
from ..lib.utils import timing
from ..names import Names as N, like, MED_WINDOW
from ..sql import StatisticName, ActivityGroup, StatisticJournal, ActivityTimespan, ActivityJournal, Source
from ..sql.tables.statistic import STATISTIC_JOURNAL_CLASSES
from ..sql.types import short_cls

log = getLogger(__name__)


class Statistics:

    def __init__(self, s, start=None, finish=None, sources=None, with_timespan=False, with_source=False,
                 activity_journal=None, activity_group=None, warn_over=1):
        '''
        Specify any general constraints when constructing the object, then request particular statistics
        using by_name and by_group.

        The final dataframe can be retrieved directly via df or, via with_, additional processing can
        be made to rename columns, add statistics, etc.
        '''
        self.__s = s
        self.__start = start
        self.__finish = finish
        self.__sources = sources if sources else []
        if activity_journal:
            if not isinstance(activity_journal, Source):
                activity_journal = ActivityJournal.at(s, activity_journal)
            self.__sources.append(activity_journal)
        self.__activity_group = ActivityGroup.from_name(s, activity_group)
        self.__with_timespan = with_timespan
        self.__with_source = with_source
        self.__warn_over = warn_over
        self.__statistic_names = {}
        self.__df = None

    def __save_name(self, statistic_name):
        if statistic_name.name in self.__statistic_names:
            if statistic_name != self.__statistic_names[statistic_name.name]:
                raise Exception(f'Ambiguous name {statistic_name.name}')
        self.__statistic_names[statistic_name.name] = statistic_name

    def __name_and_type(self, name, owner, like):
        try:
            owner_name = short_cls(owner) if not isinstance(owner, str) else owner
            q = self.__s.query(StatisticName).filter(StatisticName.owner == owner)
            if like:
                statistic_names = q.filter(StatisticName.name.ilike(name)).all()
            else:
                statistic_names = [q.filter(StatisticName.name == name).one()]
            found = 0
            for statistic_name in statistic_names:
                self.__save_name(statistic_name)
                type_class = STATISTIC_JOURNAL_CLASSES[statistic_name.statistic_journal_type]
                found += 1
                yield statistic_name, type_class
            if not found:
                log.warning(f'Did not match {owner_name}.{name} (like={like})')
        except Exception:
            log_current_exception(traceback=False)
            log.warning(f'Could not match {owner_name}.{name} (like={like})')

    def __columns(self, type_class, label):
        columns = [type_class.time.label(N.INDEX), type_class.value.label(label)]
        if self.__with_source:
            columns += [type_class.source_id.label(N._src(label))]
        return columns

    def by_name(self, owner, *names, like=False):
        for name in names:
            for statistic_name, type_class in self.__name_and_type(name, owner, like):
                label = statistic_name.name
                log.info(f'Retrieving {label}')
                q = self.__s.query(*self.__columns(type_class, label)). \
                    filter(type_class.statistic_name_id == statistic_name.id)
                q = self.__constrain_journal(q)
                with timing(f'{label}\n{q}', self.__warn_over):
                    df = pd.read_sql_query(sql=q.selectable, con=self.__s.connection(), index_col=N.INDEX)
                self.__merge(df)
        return self

    def by_group(self, owner, *names, like=False):
        for name in names:
            for statistic_name, type_class in self.__name_and_type(name, owner, like):
                q_group_ids = self.__s.query(distinct(Source.activity_group_id)). \
                    join(StatisticJournal, StatisticJournal.source_id == Source.id). \
                    filter(StatisticJournal.statistic_name_id == statistic_name.id)
                q_group_ids = self.__constrain_journal(q_group_ids)
                with timing(f'group ids\n{q_group_ids}', self.__warn_over):
                    activity_group_ids = q_group_ids.all()
                for row in activity_group_ids:
                    activity_group_id = row[0]
                    if activity_group_id:
                        activity_group = self.__s.query(ActivityGroup). \
                            filter(ActivityGroup.id == activity_group_id).one()
                        label = statistic_name.name + ':' + activity_group.name
                    else:
                        label = statistic_name.name
                    log.info(f'Retrieving {label}')
                    q = self.__s.query(*self.__columns(type_class, label)). \
                        filter(type_class.statistic_name_id == statistic_name.id). \
                        join(Source, type_class.source_id == Source.id). \
                        filter(Source.activity_group_id == activity_group_id)
                    q = self.__constrain_journal(q)
                    with timing(f'{label}\n{q}', self.__warn_over):
                        df = pd.read_sql_query(sql=q.selectable, con=self.__s.connection(), index_col=N.INDEX)
                    self.__merge(df)
        return self

    def __constrain_journal(self, q):
        if self.__start: q = q.filter(StatisticJournal.time >= self.__start)
        if self.__finish: q = q.filter(StatisticJournal.time < self.__finish)
        for source in self.__sources: q = q.filter(StatisticJournal.source == source)
        if self.__activity_group:
            source = aliased(Source)
            q = q.join(source, source.id == StatisticJournal.source_id). \
                filter(source.activity_group_id == self.__activity_group.id)
        return q

    def __merge(self, df):
        if self.__df is None:
            self.__df = df
        else:
            with timing(f'merge {df.columns}', self.__warn_over):
                self.__df = self.__df.join(df, how='outer')

    def __add_timespan(self):
        self.__df[N.TIMESPAN_ID] = np.nan
        for id, start, finish in self.__s.query(ActivityTimespan.id,
                                                ActivityTimespan.start, ActivityTimespan.finish). \
                filter(ActivityTimespan.activity_journal_id.in_([source.id for source in self.__sources])):
            self.__df.loc[start:finish, [N.TIMESPAN_ID]] = id

    @property
    def df(self):
        if self.__with_timespan:
            self.__add_timespan()
            self.__with_timespan = False
        return self.__df

    @property
    def with_(self):
        return Data(self.df, self.__statistic_names)


class Data:

    def __init__(self, df, statistic_names):
        self.df = df
        self.__statistic_names = statistic_names
        log.debug(f'Columns: {", ".join(self.df.columns)}')

    def __bool__(self):
        return not self.df.dropna(how='all').empty

    def drop_prefix(self, prefix):
        for column in like(prefix + '%', self.df.columns):
            self.df.rename(columns={column: column.replace(prefix, '')}, inplace=True)
        return self
    
    def transform(self, name, scale=1.0, median=None):
        if scale != 1:
            self.df[name] = self.df[name] * scale
        if median:
            self.df[name] = self.df[name].rolling(median, min_periods=1).median()

    def __rename(self, name, new_name, scale=1.0, median=None):
        log.debug(f'{name} -> {new_name}')
        self.df.rename(columns={name: new_name}, inplace=True)
        self.transform(new_name, scale=scale, median=median)

    def __copy(self, name, new_name, scale=1.0, median=None):
        log.debug(f'{name} <-> {new_name}')
        self.df[new_name] = self.df[name]
        self.transform(new_name, scale=scale, median=median)

    def __with_names_values(self, op, map, scale=1.0, median=None):
        for name, value in map.items():
            if present(self.df, name):
                op(name, value, scale=scale, median=median)
            else:
                log.warning(f'Missing {name} in data')
        return self

    def rename(self, map, scale=1.0, median=None):
        return self.__with_names_values(self.__rename, map, scale=scale, median=median)

    def copy(self, map, scale=1.0, median=None):
        return self.__with_names_values(self.__copy, map, scale=scale, median=median)

    def __with_names_units(self, op, columns):
        for column in columns:
            if ':' in column:
                name, group = column.split(':', 1)
            else:
                name, group = column, None
            statistic_name = self.__statistic_names[name]
            if group:
                new_name = N._slash(name, statistic_name.units) + ':' + group
            else:
                new_name = N._slash(name, statistic_name.units)
            op(column, new_name)
        return self

    def rename_with_units(self, *columns):
        if not columns: columns = self.df.columns
        return self.__with_names_units(self.__rename, columns)

    def copy_with_units(self, *columns):
        if not columns: columns = self.df.columns
        return self.__with_names_units(self.__copy, columns)

    def into(self, df, tolerance, interpolate=False):
        if self:
            extra = self.df
            if interpolate: extra = extra.interpolate(method='time')
            extra = extra.reindex(df.index, method='nearest', tolerance=tolerance)
            return df.merge(extra, how='left', left_index=True, right_index=True)
        else:
            return df

    def add_times(self):
        set_times_from_index(self.df)
        return self

    def coallesce(self, *names, delete=False):
        '''
        Merge columns named with groups.
        '''
        if not names:
            names = set(column.split(':')[0] for column in self.df.columns if ':' in column)
        log.debug(f'Coallescing {names}')
        for name in names:
            if name in self.df.columns:
                raise Exception(f'{name} already exists')
            columns = like(name + ':%', self.df.columns)
            log.debug(f'Coallescing {columns} for {name}')
            df = self.df[columns].copy()
            df.fillna(method='ffill', axis='columns', inplace=True)
            df.fillna(method='bfill', axis='columns', inplace=True)
            self.df.loc[:, name] = df.iloc[:, [0]]
            if delete:
                self.df.drop(columns=columns, inplace=True)
        return self


def set_times_from_index(df):
    df.loc[:, N.TIME] = pd.to_datetime(df.index)
    df.loc[:, N.LOCAL_TIME] = df[N.TIME].apply(lambda x: time_to_local_time(x.to_pydatetime(), YMD))


def std_health_statistics(s, freq='1h'):

    from ..pipeline.owners import RestHRCalculator, ResponseCalculator, ActivityCalculator, MonitorCalculator

    start = s.query(StatisticJournal.time). \
        filter(StatisticJournal.time > local_date_to_time(to_date('1970-01-03'))). \
        order_by(asc(StatisticJournal.time)).limit(1).scalar()
    finish = s.query(StatisticJournal.time).order_by(desc(StatisticJournal.time)).limit(1).scalar()

    stats = pd.DataFrame(index=pd.date_range(start=start, end=finish, freq=freq))
    set_times_from_index(stats)

    stats = Statistics(s). \
        by_name(ResponseCalculator, N.DEFAULT_ANY, like=True).with_. \
        drop_prefix(N.DEFAULT + '_').into(stats, tolerance='30m')

    stats = Statistics(s). \
        by_name(RestHRCalculator, N.REST_HR). \
        by_name(MonitorCalculator, N.DAILY_STEPS). \
        by_name(ActivityCalculator, N._delta(N.DEFAULT_ANY), like=True).with_. \
        rename_with_units(N.REST_HR).into(stats, tolerance='30m')

    stats = Statistics(s).\
        by_group(ActivityCalculator, N.ACTIVE_TIME, N.ACTIVE_DISTANCE).with_. \
        coallesce(N.ACTIVE_TIME, N.ACTIVE_DISTANCE). \
        rename_with_units(N.ACTIVE_TIME, N.ACTIVE_DISTANCE). \
        copy({N.ACTIVE_TIME_S: N.ACTIVE_TIME_H}, scale=1 / 3600). \
        into(stats, tolerance='30m')

    return stats


def std_activity_statistics(s, activity_journal, activity_group=None):

    # the choice of which values have units is somewhat arbitrary, but less so than it was...

    from ..pipeline.calculate.elevation import ElevationCalculator
    from ..pipeline.calculate.impulse import ImpulseCalculator
    from ..pipeline.calculate.power import PowerCalculator
    from ..pipeline.read.segment import SegmentReader

    if not isinstance(activity_journal, ActivityJournal):
        activity_journal = ActivityJournal.at(s, activity_journal, activity_group=activity_group)

    stats = Statistics(s, activity_journal=activity_journal, with_timespan=True). \
        by_name(SegmentReader, N.LATITUDE, N.LONGITUDE, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y,
                N.DISTANCE, N.SPEED, N.CADENCE, N.ALTITUDE, N.HEART_RATE).with_. \
        rename_with_units(N.LATITUDE, N.LONGITUDE, N.DISTANCE, N.SPEED, N.CADENCE, N.ALTITUDE, N.HEART_RATE). \
        copy({N.SPEED_MS: N.MED_SPEED_KMH}, scale=3.6, median=MED_WINDOW). \
        copy({N.HEART_RATE_BPM: N.MED_HEART_RATE_BPM}, median=MED_WINDOW). \
        copy({N.CADENCE_RPM: N.MED_CADENCE_RPM}, median=MED_WINDOW). \
        add_times().df

    stats = Statistics(s, activity_journal=activity_journal). \
        by_name(ElevationCalculator, N.ELEVATION, N.GRADE).with_. \
        rename_with_units().into(stats, tolerance='1s')

    hr_impulse_10 = N.DEFAULT + '_' + N.HR_IMPULSE_10
    stats = Statistics(s, activity_journal=activity_journal). \
        by_name(ImpulseCalculator, N.HR_ZONE, hr_impulse_10).with_. \
        drop_prefix(N.DEFAULT + '_').into(stats, tolerance='10s', interpolate=True)

    stats = Statistics(s, activity_journal=activity_journal). \
        by_name(PowerCalculator, N.POWER_ESTIMATE).with_. \
        rename_with_units(). \
        copy({N.POWER_ESTIMATE_W: N.MED_POWER_ESTIMATE_W}, median=MED_WINDOW). \
        into(stats, tolerance='1s')

    return stats


if __name__ == '__main__':

    from ..pipeline.owners import ActivityCalculator, SegmentReader, MonitorCalculator

    s = session('-v5')

    with timing('select'):
        df = std_health_statistics(s)
        # df = std_activity_statistics(s, '2020-05-15', 'road')
        # df = Statistics(s).like(N.CLIMB_ANY, owner=ActivityCalculator).from_(activity_journal='2020-05-15').by_group().df
        # df = Statistics(s).for_(N.ACTIVE_DISTANCE, owner=ActivityCalculator).by_group()
        # acc = Accumulator(s, sources=[ActivityJournal.at(s, '2020-05-15')])
        # acc = Accumulator(s, with_timespan=True, sources=[ActivityJournal.at(s, '2020-05-15')])
        # acc = Accumulator(s, with_source=True)
        # acc.by_name(ActivityCalculator, N.CLIMB_ANY, like=True)
        # df = acc.df

    print(df)
    print(df.describe())
    print(df.columns)
    print(df[N.DAILY_STEPS].describe())
