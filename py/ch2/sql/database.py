from contextlib import contextmanager
from logging import getLogger
from os.path import exists
from sqlite3 import OperationalError, Connection

from sqlalchemy import create_engine, event, MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql.functions import count
from uritools import urisplit

from . import *
from .support import Base
from ..commands.args import NamespaceWithVariables, NO_OP, make_parser, DB_EXTN, base_system_path, DATA, ACTIVITY, \
    DB_VERSION, POSTGRESQL, SQLITE
from ..lib.io import touch
from ..lib.log import make_log_from_args
from ..lib.utils import grouper

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
Timestamp, Process, SystemConstant


log = getLogger(__name__)

# https://stackoverflow.com/questions/13712381/how-to-turn-on-pragma-foreign-keys-on-in-sqlalchemy-migration-script-or-conf
@event.listens_for(Engine, "connect")
def fk_pragma_on_connect(dbapi_con, _con_record):
    if isinstance(dbapi_con, Connection):  # sqlite
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
    if isinstance(dbapi_con, Connection):  # sqlite
        cursor = dbapi_con.cursor()
        try:
            # this can fail if another process is using the database
            cursor.execute("PRAGMA optimize;")  # https://www.sqlite.org/pragma.html#pragma_optimize
        except OperationalError as e:
            log.debug("Optimize DB aborted (DB likely still in use)")
        finally:
            cursor.close()


def scheme(uri):
    return urisplit(uri).scheme


def sqlite_uri(base, read_only=False, name=ACTIVITY, version=DB_VERSION):
    path = base_system_path(base, subdir=DATA, file=name + DB_EXTN, version=version)
    uri = f'{SQLITE}:///{path}'
    if read_only: uri += '?mode=ro'
    return uri


def postgresql_uri(read_only=False, version=DB_VERSION):
    '''
    We no longer use base here.  It was a confused mess.  You can still have a database that depends on base
    because the system database still switches, so you can explicitly configure a different database uri.

    We use the default postgres schema because they cannot be managed within the URI.
    See also https://docs.sqlalchemy.org/en/13/dialects/postgresql.html#remote-schema-table-introspection-and-postgresql-search-path
    '''
    if read_only: log.warning('Read-only not supported yet for Postgres')
    name = f'{ACTIVITY}-{version}'
    return f'{POSTGRESQL}://postgres@localhost/{name}'


class DirtySession(Session):
    '''Extend Session to record dirty intervals and then mark those intervals when the current transaction ends.'''

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.__dirty_ids = set()

    def record_dirty_intervals(self, ids):
        self.__dirty_ids.update(ids)

    def __mark_dirty_intervals(self):
        if self.__dirty_ids:
            log.debug(f'Marking {len(self.__dirty_ids)} as dirty')
            for ids in grouper(self.__dirty_ids, 900):
                self.query(Interval).filter(Interval.id.in_(ids)). \
                    update({Interval.dirty: True}, synchronize_session=False)
            super().commit()
            self.__dirty_ids = set()

    def commit(self):
        super().commit()
        self.__mark_dirty_intervals()

    def rollback(self):
        super().rollback()
        self.__dirty_ids = set()


class DatabaseBase:

    def __init__(self, uri):
        self.uri = uri
        log.info('Using database at %s' % self.uri)
        options = {'echo': False}
        uri_parts = urisplit(uri)
        if POSTGRESQL == uri_parts.scheme: options.update(executemany_mode="values")
        if SQLITE == uri_parts.scheme and not exists(uri_parts.path): touch(uri_parts.path, with_dirs=True)
        log.debug(f'Creating engine for {uri} with options {options}')
        self.engine = create_engine(uri, **options)
        self.session = sessionmaker(bind=self.engine, class_=DirtySession)

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
        return f'{self.__class__.__name__} at {self.uri}'


class Database(DatabaseBase):

    def __init__(self, uri):
        super().__init__(uri)
        if self.no_schema(Source):
            log.info('Creating tables')
            Base.metadata.create_all(self.engine)

    def no_data(self):
        with self.session_context() as s:
            n_topics = s.query(count(DiaryTopic.id)).scalar()
            n_activities = s.query(count(ActivityGroup.id)).scalar()
            n_statistics = s.query(count(StatisticName.id)).scalar()
            return not (n_topics + n_activities + n_statistics)

    def no_schema(self, table=Constant):
        return super().no_schema(table=table)


def connect(args):
    '''
    Bootstrap from commandline-like args.
    '''
    from .system import Data
    if len(args) == 1 and isinstance(args[0], str):
        args = args[0].split()
    elif args:
        args = list(args)
    else:
        args = []
    args.append(NO_OP)
    ns = NamespaceWithVariables(make_parser(with_noop=True).parse_args(args))
    make_log_from_args(ns)
    data = Data(ns)
    return ns, data.db


class ReflectedDatabase(DatabaseBase):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)
