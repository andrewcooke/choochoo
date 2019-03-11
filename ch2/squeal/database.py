
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.functions import count

from . import *
from .support import Base
from ..command.args import DATABASE, NamespaceWithVariables, NO_OP, parser
from ..lib.log import make_log

# mention these so they are "created"
Source,  Interval,
ActivityGroup, ActivityJournal, ActivityTimespan,
Topic, TopicJournal,
StatisticName, StatisticJournal, StatisticJournalInteger, StatisticJournalFloat, StatisticJournalText,
Segment, SegmentJournal
Pipeline
MonitorJournal
Constant, SystemConstant
ActivitySimilarity, ActivityNearby


# https://stackoverflow.com/questions/13712381/how-to-turn-on-pragma-foreign-keys-on-in-sqlalchemy-migration-script-or-conf
@event.listens_for(Engine, "connect")
def fk_pragma_on_connect(dbapi_con, _con_record):
    cursor = dbapi_con.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")  # https://www.sqlite.org/pragma.html#pragma_foreign_keys
    cursor.execute("PRAGMA temp_store=MEMORY;")  # https://www.sqlite.org/pragma.html#pragma_temp_store
    cursor.execute("PRAGMA threads=4;")  # https://www.sqlite.org/pragma.html#pragma_threads
    cursor.execute("PRAGMA cache_size=-1000000;")  # 1GB  https://www.sqlite.org/pragma.html#pragma_cache_size
    cursor.execute("PRAGMA secure_delete=OFF;")  # https://www.sqlite.org/pragma.html#pragma_secure_delete
    # cursor.execute("PRAGMA journal_mode=WAL;")  # https://www.sqlite.org/wal.html
    cursor.close()


@event.listens_for(Engine, 'close')
def analyxe_pragma_on_close(dbapi_con, _con_record):
    cursor = dbapi_con.cursor()
    cursor.execute("PRAGMA optimize;")  # https://www.sqlite.org/pragma.html#pragma_optimize
    cursor.close()


class Database:

    def __init__(self, args, log):
        self._log = log
        path = args.file(DATABASE)
        self._log.info('Using database at %s' % path)
        self.engine = create_engine('sqlite:///%s' % path, echo=False)
        self.session = sessionmaker(bind=self.engine)
        self.__create_tables()

    def __create_tables(self):
        if self.is_empty(tables=True):
            self._log.info('Creating tables')
            Base.metadata.create_all(self.engine)

    @contextmanager
    def session_context(self):
        session = self.session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def is_empty(self, tables=False):
        if tables:
            # https://stackoverflow.com/questions/33053241/sqlalchemy-if-table-does-not-exist
            return not self.engine.dialect.has_table(self.engine, Source.__tablename__)
        else:
            with self.session_context() as s:
                n_topics = s.query(count(Topic.id)).scalar()
                n_activities = s.query(count(ActivityGroup.id)).scalar()
                n_statistics = s.query(count(StatisticName.id)).scalar()
            return not (n_topics + n_activities + n_statistics)


def add(s, instance):
    s.add(instance)
    return instance


def connect(args):
    '''
    Bootstrap from commandline-like args.
    '''
    if len(args) == 1:
        args = args[0].split()
    elif args:
        args = list(args)
    else:
        args = []
    args.append(NO_OP)
    ns = NamespaceWithVariables(parser().parse_args(args))
    log = make_log(ns)
    db = Database(ns, log)
    return ns, log, db

