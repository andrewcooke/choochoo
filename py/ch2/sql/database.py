from contextlib import contextmanager
from logging import getLogger

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql.functions import count
from sqlalchemy_utils import create_database
from uritools import urisplit

from . import *
from .support import Base
from ..commands.args import NO_OP, make_parser, NamespaceWithVariables, PROGNAME, DB_VERSION
from ..common.names import POSTGRESQL
from ..common.sql import database_really_exists
from ..lib.log import make_log_from_args
from ..lib.utils import grouper

# mention these so they are "created" (todo - is this needed? missing tables seem to get created anyway)

Source,  Interval, Composite, CompositeComponent
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


def scheme(uri):
    return urisplit(uri).scheme


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
        options = {'echo': False}
        uri_parts = urisplit(uri)
        # todo - could be part of uri?
        if POSTGRESQL == uri_parts.scheme: options.update(executemany_mode="values")
        if not database_really_exists(uri):
            log.warning(f'Creating database at {uri}')
            create_database(uri)
        log.debug(f'Creating engine with options {options}')
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
    ns = NamespaceWithVariables(make_parser(with_noop=True).parse_args(args), PROGNAME, DB_VERSION)
    make_log_from_args(ns)
    data = Data(ns)
    return ns, data.db


class ReflectedDatabase(DatabaseBase):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)


