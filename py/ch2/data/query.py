
'''
new interface for reading from the database.

try to have a 'fluent interface' that allows progressive refinement through the following stages:
* specifying the statistics to retrieve
* retrieving the dataframe
* modifying the dataframe
'''

from collections import Counter, defaultdict
from logging import getLogger

import pandas as pd
from sqlalchemy import or_, inspect, select, and_, asc, desc, distinct

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

# todo - isn't this defined elsewhere?

def _tables():
    return kargs_to_attr(sj=inspect(StatisticJournal).local_table,
                         sn=inspect(StatisticName).local_table,
                         sji=inspect(StatisticJournalInteger).local_table,
                         sjf=inspect(StatisticJournalFloat).local_table,
                         sjt=inspect(StatisticJournalText).local_table,
                         inv=inspect(Interval).local_table,
                         at=inspect(ActivityTimespan).local_table,
                         ag=inspect(ActivityGroup).local_table,
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

    def __init__(self, s):
        self.__session = s
        self.__statistic_names = []
        self.__start = None
        self.__finish = None
        self.__activity_journal = None
        self.__with_timespan = False
        self.__with_source = False

    def __check(self, statistic_names, owner):
        if not (statistic_names or owner):
            raise Exception('Provide at least one constraint')
        if not owner: log.warning('Querying without owner')

    def for_(self, *statistic_names, owner=None):
        log.debug(f'For {", ".join(statistic_names)}; {owner}')
        self.__check(statistic_names, owner)
        q = self.__session.query(StatisticName)
        if statistic_names:
            q = q.filter(StatisticName.name.in_(statistic_names))
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
                log.debug(f'  {statistic_name.name} owner {statistic_name.owner}')
            if not q.count():
                log.debug(f'  does not match and owner or activity group')

    def like(self, *statistic_names, owner=None):
        log.debug(f'Like {", ".join(statistic_names)}; {owner}')
        self.__check(statistic_names, owner)
        q = self.__session.query(StatisticName)
        if statistic_names:
            q = q.filter(or_(*[StatisticName.name.ilike(statistic_name) for statistic_name in statistic_names]))
        if owner:
            q = q.filter(StatisticName.owner.ilike(owner))
        found = q.all()
        if found:
            log.debug(f'Appending {len(found)} statistics names ({len(statistic_names)} patterns)')
        else:
            log.warning(f'Appending no statistic names ({", ".join(statistic_names)}; {owner})')
        found_names = set(statistic_name.name for statistic_name in found)
        missing = [statistic_name for statistic_name in statistic_names if not like(statistic_name, found_names)]
        self.__dump_matches(missing)
        self.__statistic_names += found
        return self

    def __iter__(self):
        return iter(self.__statistic_names)

    def __bool__(self):
        return bool(self.__statistic_names)

    def from_(self, start=None, finish=None, activity_journal=None, activity_group=None,
              with_timespan=False, with_source=False):
        self.__start = start
        self.__finish = finish
        if activity_journal:
            if not isinstance(activity_journal, ActivityJournal):
                activity_journal = ActivityJournal.at(self.__session, activity_journal, activity_group=activity_group)
            self.__activity_journal = activity_journal
        if with_timespan:
            if not self.__activity_journal: raise Exception('Timespan only available with activity journal')
        self.__with_timespan = with_timespan
        self.__with_source = with_source
        return self

    def __build_core_query(self, T, columns):
        core_select = select(columns).select_from(T.sj). \
            where(T.sj.c.statistic_name_id.in_([statistic_name.id for statistic_name in self.__statistic_names]))
        if self.__start: core_select = core_select.where(T.sj.c.time >= self.__start)
        if self.__finish: core_select = core_select.where(T.sj.c.time < self.__finish)
        if self.__activity_journal: core_select = core_select.where(T.sj.c.source_id == self.__activity_journal.id)
        return core_select

    def __build_statistic_query(self, T, J, statistic_name, label):
        statistic_journal_type = J[statistic_name.statistic_journal_type]
        selects = [statistic_journal_type.c.value, T.sj.c.time]
        if self.__with_source: selects += [T.sj.c.source_id]
        query = select(selects). \
            select_from(T.sj.join(statistic_journal_type)). \
            where(T.sj.c.statistic_name_id == statistic_name.id)
        # order_by doesn't affect plan but seems to speed up query
        query = query.order_by(T.sj.c.time).alias('sub_' + label)
        return query, label

    def by_name(self):
        T = _tables()
        J = _type_to_journal(T)

        time_query = self.__build_core_query(T, [distinct(T.sj.c.time).label('time')]). \
            order_by(T.sj.c.time).alias('sub_time')
        statistic_queries = [self.__build_statistic_query(T, J, statistic_name, statistic_name.name)
                             for statistic_name in self.__statistic_names]

        all_selects = [time_query.c.time.label(N.INDEX)] + \
                      [query.c.value.label(label) for query, label in statistic_queries]
        if self.__with_source:
            all_selects += [query.c.source_id.label(N._src(label)) for query, label in statistic_queries]

        all_froms = time_query
        for query, _ in statistic_queries:
            all_froms = all_froms.outerjoin(query, time_query.c.time == query.c.time)
        if self.__with_timespan:
            all_selects += [T.at.c.id.label(N.TIMESPAN_ID)]
            all_froms = all_froms.outerjoin(T.at,
                                            and_(T.at.c.start <= time_query.c.time,
                                                 T.at.c.finish > time_query.c.time,
                                                 T.at.c.activity_journal_id == self.__activity_journal.id))

        return Data(self.__session, select(all_selects).select_from(all_froms), self.__statistic_names)

    def __build_group_select(self, T, J, activity_group_id, grouped_names, id_select):

        log.debug(f'Processing group {activity_group_id}')

        time_query = select([distinct(id_select.c.time).label('time')]). \
            select_from(id_select). \
            where(id_select.c.activity_group_id == activity_group_id). \
            alias('sub_time')
        statistic_queries = [self.__build_statistic_query(T, J, statistic_name,
                                                          statistic_name.name + ':' + activity_group_name)
                             for statistic_name, activity_group_name in grouped_names[activity_group_id]]

        all_selects = [time_query.c.time.label(N.INDEX)] + \
                      [query.c.value.label(label) for query, label in statistic_queries]
        if self.__with_source:
            all_selects += [query.c.source_id.label(N._src(label)) for query, label in statistic_queries]

        all_froms = time_query
        for query, _ in statistic_queries:
            all_froms = all_froms.outerjoin(query, time_query.c.time == query.c.time)
        if self.__with_timespan:
            all_selects += [T.at.c.id.label(N.TIMESPAN_ID)]
        all_froms = all_froms.outerjoin(T.at,
                                        and_(T.at.c.start <= time_query.c.time,
                                             T.at.c.finish > time_query.c.time,
                                             T.at.c.activity_journal_id == self.__activity_journal.id))

        group_query = select(all_selects).select_from(all_froms)
        return group_query, [label for _, label in statistic_queries]

    def __get_grouped_names(self, T):
        names_by_id = {statistic_name.id: statistic_name for statistic_name in self.__statistic_names}
        group_select = self.__build_core_query(T, [T.sj.c.statistic_name_id, T.ag.c.id, T.ag.c.name]). \
            distinct(). \
            select_from(T.src).where(T.sj.c.source_id == T.src.c.id). \
            select_from(T.ag).where(T.src.c.activity_group_id == T.ag.c.id)
        grouped_names = defaultdict(list)
        for row in s.execute(group_select):
            grouped_names[row[1]].append((names_by_id[row[0]], row[2]))
        log.debug(f'Grouped names: {grouped_names}')
        return grouped_names

    def by_group(self):
        T = _tables()
        J = _type_to_journal(T)
        grouped_names = self.__get_grouped_names(T)

        id_select = self.__build_core_query(T, [T.sj.c.time, T.sj.c.id, T.src.c.activity_group_id]). \
            select_from(T.src).where(T.sj.c.source_id == T.src.c.id).cte()

        group_selects_and_labels = [self.__build_group_select(T, J, activity_group_id, grouped_names, id_select)
                                    for activity_group_id in grouped_names]



        for activity_group_id in grouped_names.keys():

            log.debug(f'Processing group {activity_group_id}')

            time_select = select([distinct(id_select.c.time).label('time')]). \
                select_from(id_select). \
                where(id_select.c.activity_group_id == activity_group_id). \
                alias('sub_time')

            statistic_selects = [self.__build_statistic_query(T, J, statistic_name,
                                                              statistic_name.name + ':' + activity_group_name)
                                 for statistic_name, activity_group_name in grouped_names[activity_group_id]]
            all_selects = [time_select.c.time.label(N.INDEX)] + \
                          [query.c.value.label(label) for query, label in statistic_selects]

            if self.__with_source:
                all_selects += [query.c.source_id.label(N._src(label)) for query, label in statistic_selects]
            source = time_select
            for query, _ in statistic_selects:
                source = source.outerjoin(query, time_select.c.time == query.c.time)
            if self.__with_timespan:
                all_selects += [T.at.c.id.label(N.TIMESPAN_ID)]
                source = source.outerjoin(T.at,
                                          and_(T.at.c.start <= time_select.c.time,
                                               T.at.c.finish > time_select.c.time,
                                               T.at.c.activity_journal_id == self.__activity_journal.id))
            full_select = select(all_selects).select_from(source)
            print(full_select)
            df = pd.read_sql_query(sql=full_select, con=self.__session.connection(), index_col=N.INDEX)
            print(df)

            exit()


class Names:

    def __init__(self, statistic_names):
        self.__by_qualified_name = {statistic_name.qualified_name: statistic_name
                                    for statistic_name in statistic_names}
        counts = Counter(statistic_name.name for statistic_name in statistic_names)
        self.__by_name = {statistic_name.name: statistic_name
                          for statistic_name in statistic_names
                          if counts[statistic_name.name] == 1}

    def __getitem__(self, name):
        if ':' in name:
            return self.__by_qualified_name[name]
        elif name in self.__by_name:
            return self.__by_name[name]
        else:
            raise Exception(f'{name} is not unique (coallesce after adding units)')


class Data:

    def __init__(self, session, query, statistic_names):
        with timing('query'):
            self.df = pd.read_sql_query(sql=query, con=session.connection(), index_col=N.INDEX)
        self.__statistic_names = Names(statistic_names)
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

    def __with_names_units(self, op, names):
        for name in names:
            statistic_name = self.__statistic_names[simple_name(name)]
            if ':' in name:
                a, b = name.split(':', 1)
                new_name = N._slash(a, statistic_name.units) + ':' + b
            else:
                new_name = N._slash(name, statistic_name.units)
            if name == statistic_name.name: new_name = simple_name(new_name)
            op(name, new_name)
        return self

    def rename_with_units(self, *names):
        return self.__with_names_units(self.__rename, names)

    def rename_all_with_units(self):
        return self.__with_names_units(self.__rename, self.df.columns)

    def copy_with_units(self, *names):
        return self.__with_names_units(self.__copy, names)

    def copy_all_with_units(self):
        return self.__with_names_units(self.__copy, self.df.columns)

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

    def coallesce(self, *names, delete=False):
        if not names:
            names = set(column.split(':')[0] for column in self.df.columns if ':' in column)
        log.debug(f'Coallescing {names}')
        for name in names:
            if name in self.df.columns:
                raise Exception(f'{name} already exists')
            columns = like(name + ':%', self.df.columns)
            log.debug(f'Coallescing {columns} for {name}')
            df = self.df[columns].copy()
            df.fillna(method='ffill', inplace=True)
            df.fillna(method='bfill', inplace=True)
            self.df.loc[:, name] = df.iloc[:, [0]]
            if delete:
                self.df.drop(columns=columns, inplace=True)
        return self


def set_times_from_index(df):
    df.loc[:, N.TIME] = pd.to_datetime(df.index)
    df.loc[:, N.LOCAL_TIME] = df[N.TIME].apply(lambda x: time_to_local_time(x.to_pydatetime(), YMD))


def std_health_statistics(s, freq='1h'):

    from ..pipeline.owners import RestHRCalculator, ResponseCalculator, ActivityCalculator

    start = s.query(StatisticJournal.time). \
        filter(StatisticJournal.time > local_date_to_time(to_date('1970-01-03'))). \
        order_by(asc(StatisticJournal.time)).limit(1).scalar()
    finish = s.query(StatisticJournal.time).order_by(desc(StatisticJournal.time)).limit(1).scalar()

    stats = pd.DataFrame(index=pd.date_range(start=start, end=finish, freq=freq))
    set_times_from_index(stats)

    stats = Statistics(s). \
        like(N.DEFAULT_ANY, owner=ResponseCalculator).by_name(). \
        drop_prefix(N.DEFAULT + '_'). \
        into(stats, tolerance='30m')

    stats = Statistics(s,). \
        for_(N.REST_HR, owner=RestHRCalculator). \
        like(N._delta(N.DEFAULT_ANY), owner=ActivityCalculator). \
        by_name().rename_all_with_units().into(stats, tolerance='30m')

    stats = Statistics(s).for_(N.ACTIVE_TIME, N.ACTIVE_DISTANCE, owner=ActivityCalculator). \
        by_name(). \
        rename_all_with_units(). \
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
                               owner=SegmentReader). \
        from_(activity_journal=activity_journal, with_timespan=True).by_name(). \
        rename_with_units(N.LATITUDE, N.LONGITUDE, N.DISTANCE, N.SPEED, N.CADENCE, N.ALTITUDE, N.HEART_RATE). \
        copy({N.SPEED_MS: N.MED_SPEED_KMH}, scale=3.6, median=MED_WINDOW). \
        copy({N.HEART_RATE_BPM: N.MED_HEART_RATE_BPM}, median=MED_WINDOW). \
        copy({N.CADENCE_RPM: N.MED_CADENCE_RPM}, median=MED_WINDOW). \
        with_times().df

    stats = Statistics(s).for_(N.ELEVATION, N.GRADE, owner=ElevationCalculator). \
        from_(activity_journal=activity_journal).by_name(). \
        rename_all_with_units().into(stats, tolerance='1s')

    hr_impulse_10 = N.DEFAULT + '_' + N.HR_IMPULSE_10
    stats = Statistics(s).for_(N.HR_ZONE, hr_impulse_10, owner=ImpulseCalculator). \
        from_(activity_journal=activity_journal).by_name().drop_prefix(N.DEFAULT + '_'). \
        into(stats, tolerance='10s', interpolate=True)

    stats = Statistics(s).for_(N.POWER_ESTIMATE, owner=PowerCalculator). \
        from_(activity_journal=activity_journal).by_name(). \
        rename_all_with_units(). \
        copy({N.POWER_ESTIMATE_W: N.MED_POWER_ESTIMATE_W}, median=MED_WINDOW). \
        into(stats, tolerance='1s')

    return stats


if __name__ == '__main__':

    from ..pipeline.owners import ActivityCalculator

    s = session('-v5')

    # df = std_health_statistics(s)
    with timing('select'):
        # df = std_activity_statistics(s, '2020-05-15', 'road')
        # df = Statistics(s).like(N.CLIMB_ANY, owner=ActivityCalculator).from_(activity_journal='2020-05-15').by_group().df
        df = Statistics(s).for_(N.ACTIVE_DISTANCE, owner=ActivityCalculator).by_group()

    print(df)
    print(df.describe())
    print(df.columns)
