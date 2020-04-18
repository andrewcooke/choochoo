
from contextlib import contextmanager
from logging import getLogger
from sqlite3 import OperationalError

from sqlalchemy import create_engine, event, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.functions import count

from . import *
from .support import Base
from ..commands.args import NamespaceWithVariables, NO_OP, make_parser, DATA, DB_EXTN, ACTIVITY
from ..lib.log import make_log_from_args


# mention these so they are "created" (todo - is this needed? missing tables seem to get created anyway)
Source,  Interval, Dummy, Composite, CompositeComponent
ActivityGroup, ActivityJournal, ActivityTimespan, ActivityBookmark
DiaryTopic, DiaryTopicJournal, DiaryTopicField,
ActivityTopic, ActivityTopicJournal, ActivityTopicField,
StatisticName, StatisticJournal, StatisticJournalInteger, StatisticJournalFloat, StatisticJournalText, StatisticMeasure
Segment, SegmentJournal
Pipeline
MonitorJournal
Constant, SystemConstant, Process
ActivitySimilarity, ActivityNearby
Timestamp


log = getLogger(__name__)

# https://stackoverflow.com/questions/13712381/how-to-turn-on-pragma-foreign-keys-on-in-sqlalchemy-migration-script-or-conf
@event.listens_for(Engine, "connect")
def fk_pragma_on_connect(dbapi_con, _con_record):
    cursor = dbapi_con.cursor()

    def pragma(cmd):
        full_cmd = f'PRAGMA {cmd}'
        cursor.execute(full_cmd)

    pragma('foreign_keys=ON;')  # https://www.sqlite.org/pragma.html#pragma_foreign_keys
    pragma('temp_store=MEMORY;')  # https://www.sqlite.org/pragma.html#pragma_temp_store
    pragma('threads=4;')  # https://www.sqlite.org/pragma.html#pragma_threads
    pragma('cache_size=-1000000;')  # 1GB  https://www.sqlite.org/pragma.html#pragma_cache_size
    pragma('secure_delete=OFF;')  # https://www.sqlite.org/pragma.html#pragma_secure_delete
    pragma('journal_mode=WAL;')  # https://www.sqlite.org/wal.html
    pragma(f'busy_timeout={5 * 60 * 1000};')  # https://www.sqlite.org/pragma.html#pragma_busy_timeout
    cursor.close()


@event.listens_for(Engine, 'close')
def analyze_pragma_on_close(dbapi_con, _con_record):
    cursor = dbapi_con.cursor()
    try:
        # this can fail if another process is using the database
        cursor.execute("PRAGMA optimize;")  # https://www.sqlite.org/pragma.html#pragma_optimize
    except OperationalError as e:
        log.debug("Optimize DB aborted (DB likely still in use)")
    finally:
        cursor.close()


class DatabaseBase:

    def __init__(self, path, read_only=False):
        self.path = path
        log.info('Using database at %s' % self.path)
        uri = f'sqlite:///{path}'
        if read_only: uri += '?mode=ro'
        log.debug(f'Connecting to {uri}')
        self.engine = create_engine(uri, echo=False)
        self.session = self._sessionmaker()

    def _sessionmaker(self):
        return sessionmaker(bind=self.engine)

    def no_schema(self, table):
        # https://stackoverflow.com/questions/33053241/sqlalchemy-if-table-does-not-exist
        return not self.engine.dialect.has_table(self.engine, table.__tablename__)

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

    def __str__(self):
        return f'{self.__class__.__name__} at {self.path}'


class MappedDatabase(DatabaseBase):

    def __init__(self, name, table, base, args, **kargs):
        super().__init__(args.system_path(DATA, name + DB_EXTN), **kargs)
        if self.no_schema(table):
            log.info('Creating tables')
            base.metadata.create_all(self.engine)


class Database(MappedDatabase):

    def __init__(self, args):
        super().__init__(ACTIVITY, Source, Base, args)

    def no_data(self,):
        with self.session_context() as s:
            n_topics = s.query(count(DiaryTopic.id)).scalar()
            n_activities = s.query(count(ActivityGroup.id)).scalar()
            n_statistics = s.query(count(StatisticName.id)).scalar()
            return not (n_topics + n_activities + n_statistics)


def connect(args):
    '''
    Bootstrap from commandline-like args.
    '''
    if len(args) == 1 and isinstance(args[0], str):
        args = args[0].split()
    elif args:
        args = list(args)
    else:
        args = []
    args.append(NO_OP)
    ns = NamespaceWithVariables(make_parser(with_noop=True).parse_args(args))
    make_log_from_args(ns)
    db = Database(ns)
    return ns, db


class ReflectedDatabase(DatabaseBase):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)

