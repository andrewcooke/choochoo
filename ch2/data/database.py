
from collections import defaultdict
from re import compile

from pandas import DataFrame
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, contains_eager, aliased
from sqlalchemy.orm.exc import NoResultFound

from ..args import parser, NamespaceWithVariables, DATA
from ..log import make_log
from ..squeal.database import Database
from ..squeal.tables.activity import Activity, ActivityStatistic, ActivityDiary
from ..squeal.tables.statistic import Statistic
from ..squeal.tables.summary import SummaryTimespan, DistributionStatistic, Summary


class Data:

    def __init__(self, log, db):
        self.__log = log
        # we use a single, long-lived session so that object access is easy
        # (we're only reading and assume the database doesn't change)
        self.__session = db.session()

    def activity(self, name):
        try:
            activity = self.__session.query(Activity). \
                options(joinedload(Activity.statistics),
                        contains_eager('statistics.activity')).filter(Activity.title == name).one()
            return ActivityData(self.__log, self.__session, activity)
        except NoResultFound:
            raise Exception('No such activity (%s)' % name)


class ActivityData:

    def __init__(self, log, session, activity):
        self.__log = log
        self.__session = session
        self.__activity = activity

    @property
    def statistic_names(self):
        return [s.name for s in self.__activity.statistics]

    def statistics(self, *names):
        return list(self.__expand_statistic_names(names))

    def __activity_starts(self):
        for start in self.__session.query(ActivityDiary.start). \
                filter(ActivityDiary.activity == self.__activity). \
                order_by(ActivityDiary.start).all():
            yield start[0]

    def __summary_starts(self):
        for start in self.__session.query(SummaryTimespan.start). \
                join(SummaryTimespan.summary). \
                filter(Summary.activity == self.__activity). \
                order_by(SummaryTimespan.start).all():
            yield start[0]

    def activity_statistics(self, *names):
        starts = list(self.__activity_starts())
        data_by_date = defaultdict(dict)
        for statistic in self.__expand_statistic_names(names):
            for (date, value) in self.__session.query(ActivityDiary.start, ActivityStatistic.value). \
                    join(ActivityDiary.statistics). \
                    filter(ActivityDiary.activity == self.__activity,
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
            for (date, q0, q1, q2, q3, q4) in self.__session.query(SummaryTimespan.start, xs[0].value, xs[1].value,
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
        if not names:
            return self.__activity.statistics
        all_names, statistics = set(), set()
        for name in names:
            if isinstance(name, Statistic):
                statistics.add(name)
            else:
                all_names.update(n.strip() for n in name.split(','))
        if all_names:
            lookup = dict((s.name, s) for s in self.__activity.statistics)
            known = set(lookup.keys())
            for name in list(all_names):
                if name in known:
                    statistics.add(lookup[name])
                    all_names.remove(name)
            for name in all_names:
                m = compile(name)
                for k in known:
                    if m.fullmatch(k):
                        statistics.add(lookup[k])
        if not statistics:
            raise Exception('Matched no statistics')
        return statistics


def data(*args):
    p = parser()
    args = list(args)
    args.append(DATA)
    ns = NamespaceWithVariables(p.parse_args(args))
    log = make_log(ns)
    db = Database(ns, log)
    return Data(log, db)
