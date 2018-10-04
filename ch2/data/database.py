
from collections import defaultdict

from pandas import DataFrame
from pygeotile.point import Point
from sqlalchemy.sql.functions import count

from ..command.args import parser, NamespaceWithVariables, NO_OP
from ..lib.log import make_log
from ..squeal.database import Database
from ..squeal.tables.activity import Activity, ActivityJournal
from ..squeal.tables.statistic import Statistic, StatisticJournal


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

    def statistics(self):
        data = defaultdict(list)
        for statistic in self._session.query(Statistic).order_by(Statistic.name):
            extract(data, statistic, 'name', 'description', 'units', 'summary', 'owner', 'constraint')
            data['count'].append(self._session.query(count(StatisticJournal.id)).
                                 filter(StatisticJournal.statistic == statistic).scalar())
        return DataFrame(data)

    def statistic_journals(self, *statistics, start=None, finish=None, owner=None, constraint=None):
        statistic_ids = []
        for statistic in statistics:
            statistic_ids.append(self._session.query(Statistic.id).filter(Statistic.name == statistic).scalar())
        q = self._session.query(StatisticJournal).join(Statistic).\
            filter(Statistic.id.in_(statistic_ids))
        if start:
            q = q.filter(StatisticJournal.time >= start)
        if finish:
            q = q.filter(StatisticJournal.time <= finish)
        if owner:
            q = q.filter(Statistic.owner == owner)
        if constraint:
            q = q.filter(Statistic.constraint == constraint)
        raw_data = defaultdict(dict)
        for journal in q.all():  # todo - eager load
            raw_data[journal.time][journal.statistic.name] = journal.value
        data, times = defaultdict(list), []
        for time in sorted(data.keys()):
            times.append(time)
            sub_data = raw_data[time]
            for statistic in statistics:
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
