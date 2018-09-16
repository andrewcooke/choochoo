from sqlalchemy.orm import joinedload, contains_eager, aliased
from sqlalchemy.orm.exc import NoResultFound

from ..args import parser, NamespaceWithVariables, DATA
from ..log import make_log
from ..squeal.database import Database
from ..squeal.tables.activity import Activity
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
    def statistics(self):
        return self.__activity.statistics


def data(*args):
    p = parser()
    args = list(args)
    args.append(DATA)
    ns = NamespaceWithVariables(p.parse_args(args))
    log = make_log(ns)
    db = Database(ns, log)
    return Data(log, db)
