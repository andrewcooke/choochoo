
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
from ..pipeline.calculate.activity import ActivityCalculator
from ..pipeline.calculate.monitor import MonitorCalculator
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


class Query:

    def __init__(self, s):
        self.__session = s
        self.__statistic_names = []
        self.__start = None
        self.__finish = None
        self.__activity_journal = None
        self.__with_timespan_id = False

    def __check(self, statistic_names, activity_group, owner):
        if not (statistic_names or activity_group or owner):
            raise Exception('Provide at least one constraint')
        if not owner: log.warning('Querying without owner')
        return f'{", ".join(statistic_names)}; {activity_group}; {owner}'

    def for_(self, *statistic_names, activity_group=None, owner=None):
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
        return self.append(q.all(), expected_count=len(statistic_names), msg=msg)

    def like(self, *statistic_names, activity_group=None, owner=None):
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
        return self.append(q.all(), msg=msg)

    def append(self, statistic_names, expected_count=None, msg='no diagnostocs'):
        if not statistic_names:
            log.warning(f'Appending no statistic names ({msg})')
        elif expected_count is not None and len(statistic_names) != expected_count:
            log.info(f'Unexpected number of statistic names ({len(statistic_names)} v {expected_count})')
        log.debug(', '.join(f'{statistic_name.qualified_name} ({statistic_name.id})'
                            for statistic_name in statistic_names))
        self.__statistic_names += statistic_names
        return self

    def __iter__(self):
        return iter(self.__statistic_names)

    def __bool__(self):
        return bool(self.__statistic_names)

    def from_(self, start=None, finish=None, activity_journal=None, activity_group=None,
              with_timespan_id=False):
        self.__start = start
        self.__finish = finish
        if activity_journal:
            if not isinstance(activity_journal, ActivityJournal):
                activity_journal = ActivityJournal.at(s, activity_journal, activity_group=activity_group)
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

    def __rename(self, name, new_name):
        log.debug(f'{name} -> {new_name}')
        self.df.rename(columns={name: new_name}, inplace=True)

    def __alias(self, name, new_name):
        log.debug(f'{name} <-> {new_name}')
        self.df[new_name] = self.df[name]

    def __with_names_values(self, op, args, kargs):
        for dict in list(args) + [kargs]:
            for name, value in dict.items():
                if present(self.df, name):
                    op(name, value)
                else:
                    log.warning(f'Missing {name} in data')
        return self

    def rename(self, *args, **kargs):
        return self.__with_names_values(self.__rename, args, kargs)

    def alias(self, *args, **kargs):
        return self.__with_names_values(self.__alias, args, kargs)

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

    def alias_with_units(self, *names):
        return self.__with_names_units(self.__alias, names)

    def alias_all_with_units(self):
        return self.__with_names_units(self.__alias, self.__statistic_names.keys())

    def into(self, df, tolerance, interpolate=False):
        if self:
            extra = self.df
            if interpolate: extra = extra.interpolate(method='time')
            extra = extra.reindex(df.index, method='nearest', tolerance=tolerance)
            return df.merge(extra, how='left', left_index=True, right_index=True)
        else:
            return df


def set_times_from_index(df):
    df[N.TIME] = pd.to_datetime(df.index)
    df[N.LOCAL_TIME] = df[N.TIME].apply(lambda x: time_to_local_time(x.to_pydatetime(), YMD))


def std_health_statistics(s, freq='1h'):

    from ..pipeline.calculate.heart_rate import RestHRCalculator
    from ..pipeline.calculate.response import ResponseCalculator

    start = s.query(StatisticJournal.time). \
        filter(StatisticJournal.time > local_date_to_time(to_date('1970-01-03'))). \
        order_by(asc(StatisticJournal.time)).limit(1).scalar()
    finish = s.query(StatisticJournal.time).order_by(desc(StatisticJournal.time)).limit(1).scalar()

    stats = pd.DataFrame(index=pd.date_range(start=start, end=finish, freq=freq))
    set_times_from_index(stats)

    stats = Query(s).like(N.DEFAULT_ANY, owner=ResponseCalculator).by_name().drop_prefix(N.DEFAULT + '_'). \
        into(stats, tolerance='30m')

    stats = Query(s).for_(N.REST_HR, owner=RestHRCalculator).by_name(). \
        rename_all_with_units().into(stats, tolerance='30m')

    stats = Query(s).for_(N.DAILY_STEPS, owner=MonitorCalculator). \
        for_(N.ACTIVE_TIME, N.ACTIVE_DISTANCE, owner=ActivityCalculator). \
        like(N._delta(N.DEFAULT_ANY), owner=ActivityCalculator).by_qualified(). \
        rename_with_units(N.ACTIVE_TIME, N.ACTIVE_DISTANCE).into(stats, tolerance='30m')

    stats[N.ACTIVE_TIME_H] = stats[N.ACTIVE_TIME_S] / 3600

    return stats


MIN_PERIODS = 1


def std_activity_statistics(s, activity_journal, activity_group=None):

    # the choice of which values have units is somewhat arbitrary, but less so than it was...

    from ..pipeline.calculate.elevation import ElevationCalculator
    from ..pipeline.calculate.impulse import ImpulseCalculator
    from ..pipeline.calculate.power import PowerCalculator
    from ..pipeline.read.segment import SegmentReader

    if not isinstance(activity_journal, ActivityJournal):
        activity_journal = ActivityJournal.at(s, activity_journal, activity_group=activity_group)

    stats = Query(s).for_(N.LATITUDE, N.LONGITUDE, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y,
                          N.DISTANCE, N.SPEED, N.CADENCE, N.ALTITUDE, N.HEART_RATE,
                          owner=SegmentReader, activity_group=activity_journal.activity_group). \
        from_(activity_journal=activity_journal, with_timespan_id=True).by_name(). \
        rename_with_units(N.LATITUDE, N.LONGITUDE, N.DISTANCE, N.SPEED, N.CADENCE, N.ALTITUDE, N.HEART_RATE).df

    stats = Query(s).for_(N.ELEVATION, N.GRADE,
                          owner=ElevationCalculator, activity_group=activity_journal.activity_group). \
        from_(activity_journal=activity_journal).by_name(). \
        rename_all_with_units().into(stats, tolerance='1s')

    hr_impulse_10 = N.DEFAULT + '_' + N.HR_IMPULSE_10
    stats = Query(s).for_(N.HR_ZONE, hr_impulse_10,
                          owner=ImpulseCalculator, activity_group=activity_journal.activity_group). \
        from_(activity_journal=activity_journal).by_name().drop_prefix(N.DEFAULT + '_'). \
        into(stats, tolerance='10s', interpolate=True)

    stats = Query(s).for_(N.POWER_ESTIMATE,
                          owner=PowerCalculator, activity_group=activity_journal.activity_group). \
        from_(activity_journal=activity_journal).by_name(). \
        rename_all_with_units().into(stats, tolerance='1s')

    stats[N.MED_SPEED_KMH] = stats[N.SPEED_MS].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median() * 3.6
    if present(stats, N.HEART_RATE_BPM):
        stats[N.MED_HEART_RATE_BPM] = stats[N.HEART_RATE_BPM].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median()
    if present(stats, N.POWER_ESTIMATE):
        stats[N.MED_POWER_ESTIMATE_W] = \
            stats[N.POWER_ESTIMATE_W].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median().clip(lower=0)
    if present(stats, N.CADENCE_RPM):
        stats[N.MED_CADENCE_RPM] = stats[N.CADENCE_RPM].rolling(MED_WINDOW, min_periods=MIN_PERIODS).median()

    set_times_from_index(stats)

    return stats


if __name__ == '__main__':
    s = session('-v5')

    df = std_activity_statistics(s, '2020-05-15')
    print(df)
    print(df.describe())
    print(df.columns)

    df = std_health_statistics(s)
    print(df)
    print(df.describe())
    print(df.columns)
