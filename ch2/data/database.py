
from collections import defaultdict
from re import compile

from pandas import DataFrame
from sqlalchemy.orm import joinedload, contains_eager
from sqlalchemy.orm.exc import NoResultFound

from ..args import parser, NamespaceWithVariables, DATA
from ..log import make_log
from ..squeal.database import Database
from ..squeal.tables.activity import Activity, ActivityStatistic, ActivityDiary
from ..squeal.tables.statistic import Statistic


class Data:

    def __init__(self, log, db):
        self.__log = log
        # we use a single, long-lived session so that object access is easy
        # (we're only reading and assume the database doesn't change)
        self.__session = db.session()

    def activity(self, name):
        try:
            activity = self.__session.query(Activity).\
                    options(joinedload(Activity.statistics),
                            contains_eager('statistics.activity')).filter(Activity.title == name).one()
            return AcitvityData(self.__log, self.__session, activity)
        except NoResultFound:
            raise Exception('No such activity (%s)' % name)


class AcitvityData:

    def __init__(self, log, session, activity):
        self.__log = log
        self.__session = session
        self.__activity = activity

    @property
    def statistic_names(self):
        return [s.name for s in self.__activity.statistics]

    def statistics(self, *names):
        return self.__expand_statistic_names(names)

    def activity_statistics(self, *names):
        names = {s.name for s in self.__expand_statistic_names(names)}
        data = defaultdict(list)
        start = []
        for diary in self.__session.query(ActivityDiary).\
                join(ActivityDiary.statistics, ActivityStatistic.statistic).\
                options(joinedload(ActivityDiary.statistics).joinedload(ActivityStatistic.statistic)).\
                filter(Statistic.activity == self.__activity).\
                order_by(ActivityDiary.start).all():
            start.append(diary.start)
            known = set()
            for statistic in diary.statistics:
                name = statistic.statistic.name
                if name in names:
                    data[name].append(statistic.value)
                    known.add(name)
            for name in names.difference(known):
                data[name].append(None)
        for s in data:
            self.__log.debug('%s: %d' % (s, len(data[s])))
        self.__log.debug('start: %d' % len(start))
        return DataFrame(data, index=start)

    def __expand_statistic_names(self, names):
        if not names:
            return self.__activity.statistics
        lookup = dict((s.name, s) for s in self.__activity.statistics)
        known = set(lookup.keys())
        all_names = set()
        for name in names:
            all_names.update(n.strip() for n in name.split(','))
        statistics = set()
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
