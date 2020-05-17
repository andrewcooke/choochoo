
'''
new interface for reading from the database.

try to have a 'fluent interface' that allows progressive refinement through the following stages:
* specifying the statistics to retrieve
* retrieving the dataframe
* modifying the dataframe
'''

from logging import getLogger

import pandas as pd
from sqlalchemy import or_, inspect, select, and_, asc, desc, distinct
from sqlalchemy.sql import func

from ..data import session, present
from ..lib import local_date_to_time, to_date, time_to_local_time
from ..lib.data import kargs_to_attr
from ..lib.date import YMD
from ..lib.utils import timing
from ..names import Names as N, like, MED_WINDOW
from ..sql import StatisticName, ActivityGroup, StatisticJournal, StatisticJournalInteger, StatisticJournalFloat, \
    StatisticJournalText, Interval, ActivityTimespan, ActivityJournal, Composite, CompositeComponent, Source, \
    StatisticJournalType
from ..sql.types import simple_name

log = getLogger(__name__)


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


def _type_to_journal(t):
    return {StatisticJournalType.INTEGER: t.sji,
            StatisticJournalType.FLOAT: t.sjf,
            StatisticJournalType.TEXT: t.sjt}


class _Qualified:

    def format(self, statistic_name):
        if statistic_name.activity_group.name == ActivityGroup.ALL:
            return statistic_name.name
        else:
            return statistic_name.name + ':' + statistic_name.activity_group.name


class Statistics:

    '''
    This is the main interface for retrieving statistics from the database.
    The code is full of examples that provide better documentation than I could write here.
    '''

    def __init__(self, s, activity_group=None):
        self.__session = s
        self.__default_activity_group = activity_group
        self.__statistic_names = []
        self.__start = None
        self.__finish = None
        self.__activity_journal = None
        self.__with_timespan_id = False

    def __with_default(self, activity_group):
        if not activity_group:
            activity_group = self.__default_activity_group
        elif self.__default_activity_group and activity_group != self.__default_activity_group:
            log.warning(f'Changing activity group {self.__default_activity_group} -> {activity_group}')
        return activity_group

    def __check(self, statistic_names, activity_group, owner):
        if not (statistic_names or activity_group or owner):
            raise Exception('Provide at least one constraint')
        if not owner: log.warning('Querying without owner')
        return f'{", ".join(statistic_names)}; {activity_group}; {owner}'

    def for_(self, *statistic_names, activity_group=None, owner=None):
        activity_group = self.__with_default(activity_group)
        msg = self.__check(statistic_names, activity_group, owner)
        q = self.__session.query(StatisticName)
        if statistic_names:
            q = q.filter(StatisticName.name.in_(statistic_names))
        if activity_group:
            if isinstance(activity_group, ActivityGroup):
                q = q.join(ActivityGroup).filter(ActivityGroup.id == activity_group.id)
            else:
                q = q.join(ActivityGroup).filter(ActivityGroup.name == activity_group)
        if owner:
            q = q.filter(StatisticName.owner == owner)
        found = q.all()
        found_names = set(statistic_name.name for statistic_name in found)
        requested_names = set(statistic_names)
        if found_names == requested_names:
            log.debug(f'Appending {len(found)} names ({len(found_names)} distinct) for '
                      f'{len(statistic_names)} requested')
        else:
            log.warning(f'Did not match all names ({len(found)} found for {len(requested_names)} requests)')
            self.__dump_matches(requested_names.difference(found_names))
        self.__statistic_names += found
        return self

    def __dump_matches(self, missing):
        for name in missing:
            log.debug(f'Request {name}:')
            q = self.__session.query(StatisticName).filter(StatisticName.name.like(name))
            for statistic_name in q.all():
                log.debug(f'  {statistic_name.name}:{statistic_name.activity_group} owner {statistic_name.owner}')
            if not q.count():
                log.debug(f'  does not match and owner or activity group')

    def like(self, *statistic_names, activity_group=None, owner=None):
        activity_group = self.__with_default(activity_group)
        msg = self.__check(statistic_names, activity_group, owner)
        q = self.__session.query(StatisticName)
        if statistic_names:
            q = q.filter(or_(*[StatisticName.name.ilike(statistic_name) for statistic_name in statistic_names]))
        if activity_group:
            if isinstance(activity_group, ActivityGroup):
                q = q.join(ActivityGroup).filter(ActivityGroup.id == activity_group.id)
            else:
                q = q.join(ActivityGroup).filter(ActivityGroup.name.ilike(activity_group))
        if owner:
            q = q.filter(StatisticName.owner.ilike(owner))
        found = q.all()
        if found:
            log.debug(f'Appending {len(found)} statistics names ({len(statistic_names)} patterns)')
        else:
            log.warning(f'Appending no statistic names ({msg})')
        found_names = set(statistic_name.name for statistic_name in found)
        missing = [statistic_name for statistic_name in statistic_names if not like(statistic_name, found_names)]
        self.__dump_matches(missing)
        return self

    def __iter__(self):
        return iter(self.__statistic_names)

    def __bool__(self):
        return bool(self.__statistic_names)

    def from_(self, start=None, finish=None, activity_journal=None, activity_group=None,
              with_timespan_id=False):
        activity_group = self.__with_default(activity_group)
        self.__start = start
        self.__finish = finish
        if activity_journal:
            if not isinstance(activity_journal, ActivityJournal):
                activity_journal = ActivityJournal.at(self.__session, activity_journal, activity_group=activity_group)
            self.__activity_journal = activity_journal
        if with_timespan_id:
            if not self.__activity_journal: raise Exception('Timespan ID only available with activity journal')
        self.__with_timespan_id = with_timespan_id
        return self

    def by_name(self, outer=False):
        return self.by('{statistic_name.name}', outer=outer)

    def by_name_group(self, outer=False):
        return self.by('{statistic_name.name}:{statistic_name.activity_group}', outer=outer)

    def by_qualified(self, outer=False):
        return self.by(_Qualified(), outer=outer)

    def by(self, template, outer=False):
        return self.__build_query(template, outer=outer)

    def __check_names(self, template):
        names = set()
        for statistic_name in self.__statistic_names:
            name = template.format(statistic_name=statistic_name)
            if name in names:
                raise Exception(f'Duplicate name {name}')
            names.add(name)

    def __build_query(self, template, outer=False):
        self.__check_names(template)
        T = _tables()
        J = _type_to_journal(T)
        if outer:
            query = self.__build_query_outer(T, J, template)
        else:
            query = self.__build_query_time(T, J, template)
        return QueryData(self.__session, query, self.__statistic_names)

    def __build_query_outer(self, T, J, template):
        '''
        build the query using an outer join on journal id for each statistic, then group by time
        and discard nulls.

        incomplete
        '''

        sj = T.sj.alias()
        selects, aliases = [sj.c.time.label(N.INDEX)], []
        for statistic_name in self.__statistic_names:
            alias = J[statistic_name.statistic_journal_type].alias()
            aliases.append(alias)
            selects.append(func.sum(alias.c.value).label(template.format(statistic_name=statistic_name)))

        source = sj
        for alias, statistic_name in zip(aliases, self.__statistic_names):
            source = source.join(alias,
                                 and_(sj.c.id == alias.c.id, sj.c.statistic_name_id == statistic_name.id),
                                 isouter=True)
        query = select(selects).select_from(source).group_by(sj.c.time).order_by(sj.c.time)
        if self.__start: query = query.where(sj.c.time >= self.__start)
        if self.__finish: query = query.where(sj.c.time < self.__finish)
        if self.__activity_journal: query = query.where(sj.c.source_id == self.__activity_journal.id)

        return query

    def __build_query_time(self, T, J, template):
        '''
        build the query by joining on time for each statistic.

        incomplete
        '''

        time_select = select([distinct(T.sj.c.time).label('time')]).select_from(T.sj). \
            where(T.sj.c.statistic_name_id.in_([statistic_name.id for statistic_name in self.__statistic_names]))
        if self.__start: time_select = time_select.where(T.sj.c.time >= self.__start)
        if self.__finish: time_select = time_select.where(T.sj.c.time < self.__finish)
        if self.__activity_journal: time_select = time_select.where(T.sj.c.source_id == self.__activity_journal.id)
        time_select = time_select.order_by('time').alias('sub_time')  # order here avoids extra index

        def statistic_select(statistic_name):
            statistic_journal = J[statistic_name.statistic_journal_type]
            query = select([statistic_journal.c.value, T.sj.c.time]). \
                select_from(T.sj.join(statistic_journal)). \
                where(T.sj.c.statistic_name_id == statistic_name.id)
            # order_by doesn't affect plan but seems to speed up query
            query = query.order_by(T.sj.c.time).alias('sub_' + template.format(statistic_name=statistic_name))
            label = template.format(statistic_name=statistic_name)
            return query, label

        all_selects = [time_select.c.time.label(N.INDEX)]
        statistic_selects = [statistic_select(statistic_name) for statistic_name in self.__statistic_names]
        all_selects += [query.c.value.label(label) for query, label in statistic_selects]
        source = time_select
        for query, _ in statistic_selects:
            source = source.outerjoin(query, time_select.c.time == query.c.time)
        if self.__with_timespan_id:
            all_selects += [T.at.c.id.label(N.TIMESPAN_ID)]
            source = source.outerjoin(T.at,
                                      and_(T.at.c.start <= time_select.c.time,
                                           T.at.c.finish > time_select.c.time,
                                           T.at.c.activity_journal_id == self.__activity_journal.id))

        query = select(all_selects).select_from(source)

        return query


class QueryData:

    def __init__(self, session, query, statistic_names):
        with timing('query'):
            self.df = pd.read_sql_query(sql=query, con=session.connection(), index_col=N.INDEX)
        self.__statistic_names = {statistic_name.name: statistic_name for statistic_name in statistic_names}

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

    def __with_names_units(self, op, names):
        for name in names:
            statistic_name = self.__statistic_names[simple_name(name)]
            new_name = N._slash(name, statistic_name.units)
            if name == statistic_name.name: new_name = simple_name(new_name)
            op(name, new_name)
        return self

    def rename_with_units(self, *names):
        return self.__with_names_units(self.__rename, names)

    def rename_all_with_units(self):
        return self.__with_names_units(self.__rename, self.__statistic_names.keys())

    def copy_with_units(self, *names):
        return self.__with_names_units(self.__copy, names)

    def copy_all_with_units(self):
        return self.__with_names_units(self.__copy, self.__statistic_names.keys())

    def into(self, df, tolerance, interpolate=False):
        if self:
            extra = self.df
            if interpolate: extra = extra.interpolate(method='time')
            extra = extra.reindex(df.index, method='nearest', tolerance=tolerance)
            return df.merge(extra, how='left', left_index=True, right_index=True)
        else:
            return df

    def with_times(self):
        set_times_from_index(self.df)
        return self


def set_times_from_index(df):
    df[N.TIME] = pd.to_datetime(df.index)
    df[N.LOCAL_TIME] = df[N.TIME].apply(lambda x: time_to_local_time(x.to_pydatetime(), YMD))


def std_health_statistics(s, freq='1h'):

    from ..pipeline import RestHRCalculator, ResponseCalculator, ActivityCalculator, MonitorCalculator

    start = s.query(StatisticJournal.time). \
        filter(StatisticJournal.time > local_date_to_time(to_date('1970-01-03'))). \
        order_by(asc(StatisticJournal.time)).limit(1).scalar()
    finish = s.query(StatisticJournal.time).order_by(desc(StatisticJournal.time)).limit(1).scalar()

    stats = pd.DataFrame(index=pd.date_range(start=start, end=finish, freq=freq))
    set_times_from_index(stats)

    stats = Statistics(s).like(N.DEFAULT_ANY, owner=ResponseCalculator).by_name().drop_prefix(N.DEFAULT + '_'). \
        into(stats, tolerance='30m')

    stats = Statistics(s).for_(N.REST_HR, owner=RestHRCalculator).by_name(). \
        rename_all_with_units().into(stats, tolerance='30m')

    stats = Statistics(s).for_(N.DAILY_STEPS, owner=MonitorCalculator). \
        for_(N.ACTIVE_TIME, N.ACTIVE_DISTANCE, owner=ActivityCalculator). \
        like(N._delta(N.DEFAULT_ANY), owner=ActivityCalculator).by_qualified(). \
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

    stats = Statistics(s).for_(N.LATITUDE, N.LONGITUDE, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y,
                               N.DISTANCE, N.SPEED, N.CADENCE, N.ALTITUDE, N.HEART_RATE,
                               owner=SegmentReader, activity_group=activity_journal.activity_group). \
        from_(activity_journal=activity_journal, with_timespan_id=True).by_name(). \
        rename_with_units(N.LATITUDE, N.LONGITUDE, N.DISTANCE, N.SPEED, N.CADENCE, N.ALTITUDE, N.HEART_RATE). \
        copy({N.SPEED_MS: N.MED_SPEED_KMH}, scale=3.6, median=MED_WINDOW). \
        copy({N.HEART_RATE_BPM: N.MED_HEART_RATE_BPM}, median=MED_WINDOW). \
        copy({N.CADENCE_RPM: N.MED_CADENCE_RPM}, median=MED_WINDOW). \
        with_times().df

    stats = Statistics(s).for_(N.ELEVATION, N.GRADE,
                               owner=ElevationCalculator, activity_group=activity_journal.activity_group). \
        from_(activity_journal=activity_journal).by_name(). \
        rename_all_with_units().into(stats, tolerance='1s')

    hr_impulse_10 = N.DEFAULT + '_' + N.HR_IMPULSE_10
    stats = Statistics(s).for_(N.HR_ZONE, hr_impulse_10,
                               owner=ImpulseCalculator, activity_group=activity_journal.activity_group). \
        from_(activity_journal=activity_journal).by_name().drop_prefix(N.DEFAULT + '_'). \
        into(stats, tolerance='10s', interpolate=True)

    stats = Statistics(s).for_(N.POWER_ESTIMATE,
                               owner=PowerCalculator, activity_group=activity_journal.activity_group). \
        from_(activity_journal=activity_journal).by_name(). \
        rename_all_with_units(). \
        copy({N.POWER_ESTIMATE_W: N.MED_POWER_ESTIMATE_W}, median=MED_WINDOW). \
        into(stats, tolerance='1s')

    return stats


if __name__ == '__main__':

    from ch2.pipeline import ActivityCalculator
    from ch2.lib.date import format_seconds

    s = session('-v5')

    df = Statistics(s, ActivityGroup.ALL). \
        for_(N.ACTIVE_DISTANCE, N.ACTIVE_TIME, N.TOTAL_CLIMB, owner=ActivityCalculator). \
        by_name().copy({N.ACTIVE_DISTANCE: N.ACTIVE_DISTANCE_KM}).with_times().df
    df['Duration'] = df[N.ACTIVE_TIME].map(format_seconds)
    if present(df, N.TOTAL_CLIMB):
        df.loc[df[N.TOTAL_CLIMB].isna(), [N.TOTAL_CLIMB]] = 0

    print(df)
    print(df.describe())
    print(df.columns)
