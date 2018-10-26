
from collections import defaultdict

from pandas import DataFrame
from pygeotile.point import Point
from sqlalchemy.sql.functions import count

from ..command.args import parser, NamespaceWithVariables, NO_OP
from ..lib.log import make_log
from ..squeal.database import Database
from ..squeal.tables.activity import Activity, ActivityJournal
from ..squeal.tables.source import Interval, Source
from ..squeal.tables.statistic import Statistic, StatisticJournal, StatisticMeasure


def extract(data, instance, *attributes):
    for attribute in attributes:
        if hasattr(instance, attribute):
            data[attribute].append(getattr(instance, attribute))
        else:
            data[attribute].append(None)


class Data:

    def __init__(self, log, db):
        self._log = log
        self._session = db.session()

    def activities(self):
        data, ids = defaultdict(list), []
        for activity in self._session.query(Activity).order_by(Activity.name):
            ids.append(activity.id)
            extract(data, activity, 'name', 'description')
            data['count'].append(self._session.query(count(ActivityJournal.id)).
                                 filter(ActivityJournal.activity == activity).scalar())
        return DataFrame(data, index=ids)

    def activity_journals(self, activity, start=None, finish=None):
        data, times = defaultdict(list), []
        q = self._session.query(ActivityJournal).join(Activity).filter(Activity.name == activity)
        if start:
            q = q.filter(ActivityJournal.time >= start)
        if finish:
            q = q.filter(ActivityJournal.time <= finish)
        for journal in q.order_by(ActivityJournal.time).all():
            times.append(journal.time)
            extract(data, journal, 'name', 'fit_file', 'finish')
        return DataFrame(data, index=times)

    def activity_waypoints(self, activity, time):
        journal = self._session.query(ActivityJournal).join(Activity). \
            filter(Activity.name == activity, ActivityJournal.time == time).one()
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
        for statistic in self._session.query(Statistic). \
                filter(Statistic.id.in_(statistic_ids)).order_by(Statistic.name):
            extract(data, statistic, 'name', 'description', 'units', 'summary', 'owner', 'constraint')
            data['count'].append(self._session.query(count(StatisticJournal.id)).
                                 filter(StatisticJournal.statistic == statistic).scalar())
        return DataFrame(data)

    def _collect_statistics(self, statistics):
        if not statistics:
            statistics = ['%']
        statistic_ids, statistic_names = set(), set()
        for statistic in statistics:
            for statistic in self._session.query(Statistic).filter(Statistic.name.like(statistic)).all():
                statistic_ids.add(statistic.id)
                statistic_names.add(statistic.name)
        return statistic_names, statistic_ids

    def _build_statistic_journal_query(self, statistic_ids, q,
            start, finish, owner, constraint):
        q = q.filter(Statistic.id.in_(statistic_ids))
        if start:
            q = q.filter(Source.time >= start)
        if finish:
            q = q.filter(Source.time <= finish)
        if owner:
            q = q.filter(Statistic.owner == owner)
        if constraint:
            q = q.filter(Statistic.constraint == constraint)
        return q

    def statistic_journals(self, *statistics, start=None, finish=None, owner=None, constraint=None, schedule=None):
        statistic_names, statistic_ids = self._collect_statistics(statistics)
        q = self._build_statistic_journal_query(
            statistic_ids, self._session.query(StatisticJournal).join(Statistic, Source),
            start, finish, owner, constraint)
        if schedule:
            q = q.join(Interval).filter(Interval.schedule == schedule)
        raw_data = defaultdict(dict)
        for journal in q.all():  # todo - eager load
            raw_data[journal.time][journal.statistic.name] = journal.value
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
        q = self._build_statistic_journal_query(
            statistic_ids, self._session.query(StatisticMeasure).join(StatisticJournal, Statistic, Source),
            start, finish, owner, constraint)
        if schedule:
            q = q.join((Interval, StatisticMeasure.source_id == Interval.id)). \
                filter(Interval.schedule == schedule)
        q = q.filter(StatisticMeasure.quartile != None)
        raw_data = defaultdict(lambda: defaultdict(lambda: [0] * 5))
        for measure in q.all():
            raw_data[measure.source.time][measure.statistic_journal.statistic.name][measure.quartile] = \
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


def data(*args):
    '''
    Start here to access data.  Create an instance in Jupyter:

        d = data('-v', '4')
        print(d.activities())
        ...
    '''
    p = parser()
    args = list(args)
    args.append(NO_OP)
    ns = NamespaceWithVariables(p.parse_args(args))
    log = make_log(ns)
    db = Database(ns, log)
    return Data(log, db)
