
'''
new interface for reading from the database.

try to have a 'fluent interface' that allows progressive refinement through the following stages:
* specifying the statistics to retrieve
* retrieving the dataframe
* modifying the dataframe
'''

from logging import getLogger
import datetime as dt

from sqlalchemy import or_, inspect, select, and_, asc, desc, distinct
from sqlalchemy.sql import func
import pandas as pd

from ch2.lib.date import YMD, time_to_local_time
from ch2.lib.utils import timing
from ch2.pipeline.calculate.activity import ActivityCalculator
from ch2.pipeline.calculate.monitor import MonitorCalculator
from ch2.pipeline.calculate.segment import SegmentCalculator
from ..lib import local_date_to_time, to_date
from ..data import session
from ..lib.data import kargs_to_attr
from ..names import Names as N, like
from ..sql import StatisticName, ActivityGroup, StatisticJournal, StatisticJournalInteger, StatisticJournalFloat, \
    StatisticJournalText, Interval, ActivityTimespan, ActivityJournal, Composite, CompositeComponent, Source, \
    StatisticJournalType

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


class Query:

    def __init__(self, s):
        self.__session = s
        self.__statistic_names = []
        self.__start = None
        self.__finish = None
        self.__activity_journal = None

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
                q = q.join(ActivityGroup).filter(ActivityGroup == activity_group)
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
                q = q.join(ActivityGroup).filter(ActivityGroup == activity_group)
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

    def from_(self, start=None, finish=None, activity_journal=None):
        self.__start = start
        self.__finish = finish
        self.__activity_journal = activity_journal  # todo date?
        return self

    def by_name(self, outer=False):
        return self.by('{statistic_name.name}', outer=outer)

    def by_name_group(self, outer=False):
        return self.by('{statistic_name.name}:{statistic_name.activity_group}', outer=outer)

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
        log.debug(query)
        return QueryData(self.__session, query)

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
        if self.__activity_journal: query = query.where(sj.c.source == self.__activity_journal.id)

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

        statistic_selects = [statistic_select(statistic_name) for statistic_name in self.__statistic_names]
        all_selects = [time_select.c.time.label(N.INDEX)] + \
             [query.c.value.label(label) for query, label in statistic_selects]
        source = time_select
        for query, _ in statistic_selects:
            source = source.outerjoin(query, time_select.c.time == query.c.time)
        query = select(all_selects).select_from(source)

        return query


class QueryData:

    def __init__(self, session, query):
        with timing('query'):
            self.df = pd.read_sql_query(sql=query, con=session.connection(), index_col=N.INDEX)

    def __bool__(self):
        return not self.df.dropna(how='all').empty

    def drop_prefix(self, prefix):
        for column in like(prefix + '%', self.df.columns):
            self.df.rename(columns={column: column.replace(prefix, '')}, inplace=True)
        return self


def std_health_statistics(s, freq='1h'):

    from ..pipeline.calculate.heart_rate import RestHRCalculator
    from ..pipeline.calculate.response import ResponseCalculator

    start = s.query(StatisticJournal.time). \
        filter(StatisticJournal.time > local_date_to_time(to_date('1970-01-03'))). \
        order_by(asc(StatisticJournal.time)).limit(1).scalar()
    finish = s.query(StatisticJournal.time).order_by(desc(StatisticJournal.time)).limit(1).scalar()

    stats = pd.DataFrame(index=pd.date_range(start=start, end=finish, freq=freq))

    def merge(extra):
        nonlocal stats
        if extra:
            extra = extra.df.reindex(stats.index, method='nearest', tolerance=dt.timedelta(minutes=30))
            stats = stats.merge(extra, how='left', left_index=True, right_index=True)

    merge(Query(s).like(N.DEFAULT_ANY, owner=ResponseCalculator).by_name().drop_prefix(N.DEFAULT + '_'))
    merge(Query(s).for_(N.REST_HR, owner=RestHRCalculator).by_name())
    merge(Query(s).for_(N.DAILY_STEPS, owner=MonitorCalculator).
          for_(N.ACTIVE_TIME, N.ACTIVE_DISTANCE, owner=ActivityCalculator).
          like(N._delta(N.DEFAULT_ANY), owner=ActivityCalculator).by_name_group())

    stats[N.ACTIVE_TIME_H] = stats[N.ACTIVE_TIME] / 3600
    stats[N.ACTIVE_DISTANCE_KM] = stats[N.ACTIVE_DISTANCE]
    stats[N.TIME] = pd.to_datetime(stats.index)
    stats[N.LOCAL_TIME] = stats[N.TIME].apply(lambda x: time_to_local_time(x.to_pydatetime(), YMD))

    return stats

'''
    def merge_to_hour(stats, extra):
        return stats.merge(extra.reindex(stats.index, method='nearest', tolerance=dt.timedelta(minutes=30)),
                           how='outer', left_index=True, right_index=True)

    # avoid x statistics some time in first day
    start = local_date_to_time(local_start, none=True) or \
            s.query(StatisticJournal.time).filter(StatisticJournal.time >
                                                  local_date_to_time(to_date('1970-01-03'))) \
                .order_by(asc(StatisticJournal.time)).limit(1).scalar()
    finish = local_date_to_time(local_finish, none=True) or \
             s.query(StatisticJournal.time).order_by(desc(StatisticJournal.time)).limit(1).scalar()
    stats = pd.DataFrame(index=pd.date_range(start=start, end=finish, freq='1h'))

    stats_1 = statistics(s, N.DEFAULT_ANY, start=start, finish=finish, check=False, owners=(ResponseCalculator,))
    if not stats_1.dropna().empty:
        for column in like(N.DEFAULT_ANY, stats_1.columns):
            stats_1.rename(columns={column: column.replace(N.DEFAULT + '_', '')}, inplace=True)
        stats_1 = stats_1.resample('1h').mean()
        stats = merge_to_hour(stats, stats_1)
    stats_2 = statistics(s, N.REST_HR, start=start, finish=finish, owners=(RestHRCalculator,), check=False)
    if present(stats_2, N.REST_HR):
        stats = merge_to_hour(stats, stats_2)
    stats_3 = statistics(s, N.DAILY_STEPS, N.ACTIVE_TIME, N.ACTIVE_DISTANCE,
                         N._delta(N.FITNESS_D_ANY), N._delta(N.FATIGUE_D_ANY), *extra,
                         start=start, finish=finish)
    stats_3 = coallesce(stats_3, N.ACTIVE_TIME, N.ACTIVE_DISTANCE)
    stats_3 = coallesce_like(stats_3, N._delta(N.FITNESS), N._delta(N.FATIGUE))
    stats = merge_to_hour(stats, stats_3)
    stats[N.ACTIVE_TIME_H] = stats[N.ACTIVE_TIME] / 3600
    stats[N.ACTIVE_DISTANCE_KM] = stats[N.ACTIVE_DISTANCE]
    stats[N.TIME] = pd.to_datetime(stats.index)
    stats[N.LOCAL_TIME] = stats[N.TIME].apply(lambda x: time_to_local_time(x.to_pydatetime(), YMD))

    return stats
'''

if __name__ == '__main__':
    s = session('-v4')
    # Query(s).for_(N.HEART_RATE, N.ACTIVE_DISTANCE, activity_group='all').by_name()
    df = std_health_statistics(s)
    print(df.describe())
    print(df.columns)