
import datetime as dt
from collections import defaultdict
from re import compile

from pandas import DataFrame
from pygeotile.point import Point
from sqlalchemy.orm import joinedload, contains_eager, aliased
from sqlalchemy.orm.exc import NoResultFound

from ..lib.args import parser, NamespaceWithVariables, NO_OP
from ..lib.log import make_log
from ..squeal.database import Database
from ..squeal.tables.activity import Activity, ActivityJournal
from ..squeal.tables.statistic import Statistic


class NameMatcher:
    
    def __init__(self, log, session):
        self._log = log
        self._session = session

    @staticmethod
    def _expand_names(type, names, defaults):
        if not names:
            return defaults
        all_names, values = set(), set()
        for name in names:
            if isinstance(name, type):
                values.add(name)
            else:
                all_names.update(n.strip() for n in name.split(','))
        if all_names:
            lookup = dict((x.name, x) for x in defaults)
            known = set(lookup.keys())
            for name in list(all_names):
                if name in known:
                    values.add(lookup[name])
                    all_names.remove(name)
            for name in all_names:
                m = compile(name)
                for k in known:
                    if m.fullmatch(k):
                        values.add(lookup[k])
        if not values:
            raise Exception('No matches')
        return values


class Data(NameMatcher):

    def __init__(self, log, db):
        # we use a single, long-lived session so that object access is easy
        # (we're only reading and assume the database doesn't change)
        super().__init__(log, db.session())

    def activity(self, name):
        try:
            activity = self._session.query(Activity). \
                options(joinedload(Activity.statistics),
                        contains_eager('statistics.activity')).filter(Activity.name == name).one()
            return ActivityData(self._log, self._session, activity)
        except NoResultFound:
            raise Exception('No such activity (%s)' % name)

    def activity_names(self):
        return [activity.name for activity in self._session.query(Activity).all()]

    def diaries(self):
        data = defaultdict(list)
        dates = []
        for diary in self._session.query(DailyDiary).all():
            dates.append(diary.date)
            data['notes'].append(diary.notes)
            data['rest heart rate'].append(diary.rest_heart_rate)
            data['sleep'].append(diary.sleep)
            data['mood'].append(diary.mood)
            data['weather'].append(diary.weather)
            data['medication'].append(diary.medication)
            data['weight'].append(diary.weight)
        return DataFrame(data, index=dates)

    def injury_names(self):
        return [injury.name for injury in self._session.query(Injury).all()]

    def injuries(self, *names):
        frames = {}
        for injury in self.__expand_injury_names(names):
            data = defaultdict(list)
            dates = []
            for diary in self._session.query(InjuryDiary).filter(InjuryDiary.injury == injury).all():
                dates.append(diary.date)
                data['pain average'].append(diary.pain_average)
                data['pain peak'].append(diary.pain_peak)
                data['pain frequency'].append(diary.pain_frequency)
                data['notes'].append(diary.notes)
            frames[injury.name] = DataFrame(data, index=dates)
        return frames

    def __expand_injury_names(self, names):
        return self._expand_names(Injury, names, self._session.query(Injury).all())


class ActivityData(NameMatcher):

    def __init__(self, log, session, activity):
        super().__init__(log, session)
        self.__activity = activity

    def statistics(self, *names):
        return list(self.__expand_statistic_names(names))

    def __activity_starts(self):
        for start in self._session.query(ActivityJournal.start). \
                filter(ActivityJournal.activity == self.__activity). \
                order_by(ActivityJournal.start).all():
            yield start[0]

    def __summary_starts(self):
        for start in self._session.query(SummaryTimespan.start). \
                join(SummaryTimespan.summary). \
                filter(Summary.activity == self.__activity). \
                order_by(SummaryTimespan.start).all():
            yield start[0]

    def activity_statistics(self, *names):
        starts = list(self.__activity_starts())
        data_by_date = defaultdict(dict)
        for statistic in self.__expand_statistic_names(names):
            for (date, value) in self._session.query(ActivityJournal.start, ActivityStatistic.value). \
                    join(ActivityJournal.statistics). \
                    filter(ActivityJournal.activity == self.__activity,
                           ActivityStatistic.statistic_id == statistic.id).all():
                data_by_date[statistic.name][date] = value
        data = defaultdict(list)
        for name in data_by_date.keys():
            stat_data = data_by_date[name]
            for start in starts:
                data[name].append(stat_data[start] if start in stat_data else None)
        return DataFrame(data, index=starts)

    def summary_statistics(self, *names):
        starts = list(self.__summary_starts())
        data_by_date = defaultdict(dict)
        for statistic in self.__expand_statistic_names(names):
            ds = [aliased(DistributionStatistic) for _ in range(5)]
            xs = [aliased(ActivityStatistic) for _ in range(5)]
            for (date, q0, q1, q2, q3, q4) in self._session.query(SummaryTimespan.start, xs[0].value, xs[1].value,
                                                                   xs[2].value, xs[3].value, xs[4].value). \
                    join(SummaryTimespan.summary). \
                    filter(Summary.activity == self.__activity,
                           ds[0].statistic_id == statistic.id, ds[0].percentile == 0,
                           ds[0].summary_timespan_id == SummaryTimespan.id,
                           ds[0].activity_statistic_id == xs[0].id,
                           ds[1].statistic_id == statistic.id, ds[1].percentile == 25,
                           ds[1].summary_timespan_id == SummaryTimespan.id,
                           ds[1].activity_statistic_id == xs[1].id,
                           ds[2].statistic_id == statistic.id, ds[2].percentile == 50,
                           ds[2].summary_timespan_id == SummaryTimespan.id,
                           ds[2].activity_statistic_id == xs[2].id,
                           ds[3].statistic_id == statistic.id, ds[3].percentile == 75,
                           ds[3].summary_timespan_id == SummaryTimespan.id,
                           ds[3].activity_statistic_id == xs[3].id,
                           ds[4].statistic_id == statistic.id, ds[4].percentile == 100,
                           ds[4].summary_timespan_id == SummaryTimespan.id,
                           ds[4].activity_statistic_id == xs[4].id).all():
                data_by_date[statistic.name][date] = (q0, q1, q2, q3, q4)
        data = defaultdict(list)
        for name in data_by_date.keys():
            stat_data = data_by_date[name]
            for start in starts:
                data[name].append(stat_data[start] if start in stat_data else None)
        return DataFrame(data, index=starts)

    def __expand_statistic_names(self, names):
        return self._expand_names(Statistic, names, self.__activity.statistics)

    def activity_diary_names(self):
        return [diary.name for diary in
                self._session.query(ActivityJournal).
                    filter(ActivityJournal.activity == self.__activity).
                    order_by(ActivityJournal.start)]

    def activity_diary(self, name):
        diary = self._session.query(ActivityJournal). \
            filter(ActivityJournal.name == name).one()
        frames = []
        for timespan in diary.timespans:
            dates = []
            data = defaultdict(list)
            for waypoint in timespan.waypoints:
                dates.append(dt.datetime.fromtimestamp(waypoint.epoch))
                data['latitude'].append(waypoint.latitude)
                data['longitude'].append(waypoint.longitude)
                if waypoint.latitude and waypoint.longitude:
                    p = Point.from_latitude_longitude(waypoint.latitude, waypoint.longitude)
                    x, y = p.meters
                else:
                    x, y = None, None
                data['x'].append(x)
                data['y'].append(y)
                data['heart rate'].append(waypoint.heart_rate)
                data['distance'].append(waypoint.distance)
                data['speed'].append(waypoint.speed)
            frames.append(DataFrame(data, index=dates))
        return frames


def data(*args):
    '''
    Start here to access data.  Create an instance in Jupyter:

        d = data('-v', '4')
        print(d.activity_names())
        ...
    '''
    p = parser()
    args = list(args)
    args.append(NO_OP)
    ns = NamespaceWithVariables(p.parse_args(args))
    log = make_log(ns)
    db = Database(ns, log)
    return Data(log, db)
