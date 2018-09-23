
from ..args import parser, NamespaceWithVariables, NO_OP
from ..log import make_log
from ..squeal.database import Database


class Session:

    def __init__(self, log, session):
        self.__log = log
        self.session = session  # only use for good...
        self.__open = True

    def __bool__(self):
        return self.__open

    def __assert_open(self):
        if not self.__open:
            raise Exception('Not open')

    def close(self, expunge=False):
        self.__assert_open()
        if expunge:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
        self.__open = False

    def all(self, cls, *filter):
        return self.session.query(cls).filter(*filter).all()

    def add(self, instance):
        self.session.add(instance)
        return instance  # for chaining


class Config:

    def __init__(self, log, db):
        self.__log = log
        self.__db = db
        self.__session = None

    def session_context(self):

        class Context:

            def __enter__(this):
                this.__session = self.session()
                return this.__session

            def __exit__(this, exc_type, exc_val, exc_tb):
                this.__session.close(expunge=exc_val)

        return Context()

    def session(self, expunge=False):
        if self.__session:
            self.__session.close(expunge=expunge)
        self.__session = Session(self.__log, self.__db.session())
        return self.__session


def config(*args):
    '''
    Start here to configure the system.  Create an instance on the command line:

        c = config('-v', '4')
        print(c...)  todo
        ...
    '''
    p = parser()
    args = list(args)
    args.append(NO_OP)
    ns = NamespaceWithVariables(p.parse_args(args))
    log = make_log(ns)
    db = Database(ns, log)
    return Config(log, db)
