
from collections import defaultdict

from pandas import DataFrame
from sqlalchemy import inspect, select
from sqlalchemy.sql.functions import count, coalesce

from ..squeal.database import connect
from ..squeal.tables.activity import ActivityGroup, ActivityJournal
from ..squeal.tables.monitor import MonitorJournal
from ..squeal.tables.source import Interval, Source
from ..squeal.tables.statistic import StatisticName, StatisticJournal, StatisticMeasure, StatisticJournalInteger, \
    StatisticJournalFloat, StatisticJournalText


def extract(data, instance, *attributes):
    for attribute in attributes:
        if hasattr(instance, attribute):
            data[attribute].append(getattr(instance, attribute))
        else:
            data[attribute].append(None)


class Data:
    '''
    Provide access to the database via DataFrames.
    Intended for use in Jupyter notebooks.
    All data retrieved in a single (read-only) session.
    '''

    def __init__(self, log, db):
        self._log = log
        self._s = db.session()

    def activity_groups(self):
        data, ids = defaultdict(list), []
        for activity_group in self._s.query(ActivityGroup).order_by(ActivityGroup.name):
            ids.append(activity_group.id)
            extract(data, activity_group, 'name', 'description')
            data['count'].append(self._s.query(count(ActivityJournal.id)).
                                 filter(ActivityJournal.activity_group == activity_group).scalar())
        return DataFrame(data, index=ids)

    def activity_journals(self, group, start=None, finish=None):
        data, times = defaultdict(list), []
        q = self._s.query(ActivityJournal).join(ActivityGroup).filter(ActivityGroup.name == group)
        if start:
            q = q.filter(ActivityJournal.finish >= start)
        if finish:
            q = q.filter(ActivityJournal.start <= finish)
        self._log.debug(q)
        for journal in q.order_by(ActivityJournal.start).all():
            times.append(journal.start)
            extract(data, journal, 'id', 'name', 'fit_file', 'finish')
        data['source_id'] = data['id']; del data['id']
        return DataFrame(data, index=times)

    def statistic_names(self, *names):
        statistic_names, statistic_ids = self._collect_statistics(names)
        data = defaultdict(list)
        for statistic in self._s.query(StatisticName). \
                filter(StatisticName.id.in_(statistic_ids)).order_by(StatisticName.name):
            extract(data, statistic, 'name', 'description', 'units', 'summary', 'owner', 'constraint')
            data['count'].append(self._s.query(count(StatisticJournal.id)).
                                 filter(StatisticJournal.statistic_name == statistic).scalar())
        return DataFrame(data)

    def _collect_statistics(self, names):
        if not names:
            names = ['%']
        statistic_ids, statistic_names = set(), set()
        for statistic_name in names:
            for statistic_name in self._s.query(StatisticName). \
                    filter(StatisticName.name.like(statistic_name)).all():
                statistic_ids.add(statistic_name.id)
                statistic_names.add(statistic_name.name)
        return statistic_names, statistic_ids

    def _build_statistic_journal_query(self, statistic_ids, start, finish, owner, constraint, source_id, schedule):

        # use more efficient expression interface and exploit the fact that
        # alternative journal types will be null in an outer join.

        sj = inspect(StatisticJournal).local_table
        sn = inspect(StatisticName).local_table
        sji = inspect(StatisticJournalInteger).local_table
        sjf = inspect(StatisticJournalFloat).local_table
        sjt = inspect(StatisticJournalText).local_table
        inv = inspect(Interval).local_table

        q = select([sn.c.name, sj.c.time, coalesce(sjf.c.value, sji.c.value, sjt.c.value)]). \
            select_from(sj.join(sn).outerjoin(sjf).outerjoin(sji).outerjoin(sjt)). \
            where(sn.c.id.in_(statistic_ids))
        if start:
            q = q.where(sj.c.time >= start)
        if finish:
            q = q.where(sj.c.time <= finish)
        if owner:
            q = q.where(sn.c.owner == owner)
        if constraint:
            q = q.where(sn.c.constraint == constraint)
        if source_id:
            q = q.where(sj.c.source_id == int(source_id))
        if schedule:
            q = q.join(inv).where(inv.c.schedule == schedule)
        q = q.order_by(sj.c.time)
        return q

    def statistic_journals(self, *statistics,
                           start=None, finish=None, owner=None, constraint=None, source_id=None, schedule=None):
        statistic_names, statistic_ids = self._collect_statistics(statistics)
        q = self._build_statistic_journal_query(statistic_ids, start, finish, owner, constraint, source_id, schedule)
        self._log.debug(q)
        data, times, err_cnt = defaultdict(list), [], defaultdict(lambda: 0)

        def pad():
            n = len(times)
            for name in statistic_names:
                if len(data[name]) != n:
                    err_cnt[name] += 1
                    if err_cnt[name] <= 1:
                        self._log.warn('Missing %s at %s (only warning for this name)' % (name, times[-1]))
                    data[name].append(None)

        for name, time, value in self._s.connection().execute(q):
            if times and times[-1] != time:
                pad()
            if not times or times[-1] != time:
                times.append(time)
            if len(data[name]) >= len(times):
                raise Exception('Duplicate data for %s at %s ' % (name, time) +
                                '(you may need to specify more constraints to make the query unique)')
            data[name].append(value)
        pad()
        self._log.debug('Loaded %d distinct times' % len(times))
        return DataFrame(data, index=times)

    def _build_statistic_quartiles_query(self, statistic_ids, q, start, finish, owner, constraint, source_id):
        q = q.filter(StatisticName.id.in_(statistic_ids))
        if start:
            q = q.filter(StatisticJournal.time >= start)
        if finish:
            q = q.filter(StatisticJournal.time <= finish)
        if owner:
            q = q.filter(StatisticName.owner == owner)
        if constraint:
            q = q.filter(StatisticName.constraint == constraint)
        if source_id:
            q = q.filter(StatisticJournal.source_id == int(source_id))
        return q

    def statistic_quartiles(self, *statistics, schedule='m',
                            start=None, finish=None, owner=None, constraint=None, source_id=None):
        statistic_names, statistic_ids = self._collect_statistics(statistics)
        q = self._s.query(StatisticMeasure). \
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
        if source_id:
            q = q.filter(StatisticJournal.source_id == int(source_id))
        if schedule:
            q = q.join((Interval, StatisticMeasure.source_id == Interval.id)). \
                filter(Interval.schedule == schedule)
        self._log.debug(q)
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
        return DataFrame(data, index=times)

    def monitor_journals(self):
        data, times = defaultdict(list), []
        for journal in self._s.query(MonitorJournal).order_by(MonitorJournal.start).all():
            times.append(journal.start)
            extract(data, journal, 'id', 'fit_file', 'finish')
        data['source_id'] = data['id']; del data['id']
        return DataFrame(data, index=times)


def data(*args):
    '''
    Start here to access data.  Create an instance in Jupyter:

        from ch2.data import data
        d = data('-v', '4')
        d.statistics()
        ...
    '''
    ns, log, db = connect(args)
    return Data(log, db)
