
from collections import defaultdict

from pandas import DataFrame
from pygeotile.point import Point
from sqlalchemy.sql.functions import count

from ..squeal.database import connect
from ..squeal.tables.activity import ActivityGroup, ActivityJournal
from ..squeal.tables.monitor import MonitorJournal
from ..squeal.tables.source import Interval, Source
from ..squeal.tables.statistic import StatisticName, StatisticJournal, StatisticMeasure

# todo
MonitorSteps = None


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
        self._session = db.session()

    def activities(self):
        data, ids = defaultdict(list), []
        for activity_group in self._session.query(ActivityGroup).order_by(ActivityGroup.name):
            ids.append(activity_group.id)
            extract(data, activity_group, 'name', 'description')
            data['count'].append(self._session.query(count(ActivityJournal.id)).
                                 filter(ActivityJournal.activity_group == activity_group).scalar())
        return DataFrame(data, index=ids)

    def activity_journals(self, activity, start=None, finish=None):
        data, times = defaultdict(list), []
        q = self._session.query(ActivityJournal).join(ActivityGroup).filter(ActivityGroup.name == activity)
        if start:
            q = q.filter(ActivityJournal.finish >= start)
        if finish:
            q = q.filter(ActivityJournal.start <= finish)
        for journal in q.order_by(ActivityJournal.start).all():
            times.append(journal.time)
            extract(data, journal, 'name', 'fit_file', 'finish')
        return DataFrame(data, index=times)

    def activity_waypoints(self, activity, time):
        journal = self._session.query(ActivityJournal).join(ActivityGroup). \
            filter(ActivityGroup.name == activity, ActivityJournal.time == time).one()
        frames = []
        for timespan in journal.timespans:
            data, times = defaultdict(list), []
            for waypoint in timespan.waypoints:
                times.append(waypoint.time)
                extract(data, waypoint, 'latitude', 'longitude', 'heart_rate', 'distance', 'speed')
                if waypoint.latitude and waypoint.longitude:
                    p = Point.from_latitude_longitude(waypoint.latitude, waypoint.longitude)
                    x, y = p.meters
                else:
                    x, y = None, None
                data['x'].append(x)
                data['y'].append(y)
            frames.append(DataFrame(data, index=times))
        return frames

    def statistics(self, *statistics):
        statistic_names, statistic_ids = self._collect_statistics(statistics)
        data = defaultdict(list)
        for statistic in self._session.query(StatisticName). \
                filter(StatisticName.id.in_(statistic_ids)).order_by(StatisticName.name):
            extract(data, statistic, 'name', 'description', 'units', 'summary', 'owner', 'constraint')
            data['count'].append(self._session.query(count(StatisticJournal.id)).
                                 filter(StatisticJournal.statistic_name == statistic).scalar())
        return DataFrame(data)

    def _collect_statistics(self, statistics):
        if not statistics:
            statistics = ['%']
        statistic_ids, statistic_names = set(), set()
        for statistic_name in statistics:
            for statistic_name in self._session.query(StatisticName). \
                    filter(StatisticName.name.like(statistic_name)).all():
                statistic_ids.add(statistic_name.id)
                statistic_names.add(statistic_name.name)
        return statistic_names, statistic_ids

    def _build_statistic_journal_query(self, statistic_ids, q,
            start, finish, owner, constraint):
        q = q.filter(StatisticName.id.in_(statistic_ids))
        if start:
            q = q.filter(Source.time >= start)
        if finish:
            q = q.filter(Source.time <= finish)
        if owner:
            q = q.filter(StatisticName.owner == owner)
        if constraint:
            q = q.filter(StatisticName.constraint == constraint)
        return q

    def statistic_journals(self, *statistics, start=None, finish=None, owner=None, constraint=None, schedule=None):
        statistic_names, statistic_ids = self._collect_statistics(statistics)
        q = self._build_statistic_journal_query(
            statistic_ids, self._session.query(StatisticJournal).join(StatisticName, Source),
            start, finish, owner, constraint)
        if schedule:
            q = q.join(Interval).filter(Interval.schedule == schedule)
        raw_data = defaultdict(dict)
        for journal in q.all():  # todo - eager load
            raw_data[journal.time][journal.statistic_name.name] = journal.value
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

    def statistic_quartiles(self, *statistics, schedule='m', start=None, finish=None, owner=None, constraint=None):
        statistic_names, statistic_ids = self._collect_statistics(statistics)
        q = self._session.query(StatisticMeasure). \
            join(StatisticJournal, StatisticMeasure.statistic_journal_id == StatisticJournal.id). \
            join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
            join(Source, StatisticJournal.source_id == Source.id)
        q = self._build_statistic_journal_query(statistic_ids, q, start, finish, owner, constraint)
        if schedule:
            q = q.join((Interval, StatisticMeasure.source_id == Interval.id)). \
                filter(Interval.schedule == schedule)
        q = q.filter(StatisticMeasure.quartile != None)
        raw_data = defaultdict(lambda: defaultdict(lambda: [0] * 5))
        for measure in q.all():
            raw_data[measure.source.time][measure.statistic_journal.statistic_name.name][measure.quartile] = \
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
        for journal in self._session.query(MonitorJournal).order_by(MonitorJournal.time).all():
            times.append(journal.time)
            extract(data, journal, 'fit_file', 'finish')
        return DataFrame(data, index=times)

    def monitor_steps(self, time):
        data, times = defaultdict(list), []
        for steps in self._session.query(MonitorSteps).join(MonitorJournal). \
                filter(MonitorJournal.time == time). \
                order_by(MonitorSteps.time).all():
            times.append(steps.time)
            extract(data, steps, 'value', 'activity')
        return DataFrame(data, index=times)

    def monitor_heart_rate(self, time):
        data, times = defaultdict(list), []
        for heart_rate in self._session.query(MonitorHeartRate).join(MonitorJournal). \
                filter(MonitorJournal.time == time). \
                order_by(MonitorHeartRate.time).all():
            times.append(heart_rate.time)
            extract(data, heart_rate, 'value')
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
