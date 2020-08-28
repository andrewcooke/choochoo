from contextlib import contextmanager
from logging import getLogger

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, Session
from uritools import urisplit, uriunsplit

from . import *
from .batch import BatchLoader
from ..commands.args import NO_OP, make_parser, NamespaceWithVariables, PROGNAME, DB_VERSION
from ..common.log import log_current_exception
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
            log.debug(f'Marking {len(self.__dirty_ids)} intervals dirty')
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


class CannotConnect(Exception): pass


class DatabaseBase:

    def __init__(self, uri):
        self.batch = BatchLoader()
        try:
            self.uri = uri
            options = {'echo': False, 'executemany_mode': 'values'}
            connect_args = {}
            uri_parts = urisplit(uri)
            if uri_parts.query:
                for name, value in uri_parts.getquerydict().items():
                    if len(value) > 1: raise Exception(f'Multiple values for option {name}')
                    value = value[0]
                    log.debug(f'Have additional URI option {name} = {value}')
                    if name == 'echo': options[name] = bool(value)
                    elif name == 'executemany_mode': options[name] = value
                    elif name == 'search_path': connect_args['options'] = f'-csearch_path={value}'
                    else: raise Exception(f'Unsupported option {name} = {value}')
                uri = uriunsplit(uri_parts._replace(query=None))
            if uri_parts.scheme != 'postgresql':
                log.warning(f'Legacy scheme {uri_parts.scheme}; discarding options')
                options, connect_args = {}, {}
            log.debug(f'Creating engine for {uri} with options {options} and connect args {connect_args}')
            self.engine = create_engine(uri, **options, connect_args=connect_args)
            self.session = sessionmaker(bind=self.engine, class_=DirtySession)
            self.engine.connect().execute(text('select 1')).fetchone()  # test connection
        except:
            log_current_exception(traceback=False)
            raise CannotConnect(f'Could not connect to database')

    def no_schema(self, table):
        # https://stackoverflow.com/questions/33053241/sqlalchemy-if-table-does-not-exist
        return not self.engine.dialect.has_table(self.engine, table.__tablename__)

    @contextmanager
    def session_context(self, **kargs):
        session = self.session(**kargs)
        self.batch.enable(session)
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

    def no_data(self):
        try:
            with self.session_context() as s:
                n_topics = s.query(DiaryTopicJournal.id).count()
                n_activities = s.query(ActivityJournal).count()
                n_statistics = s.query(StatisticJournal).count()
                return not (n_topics + n_activities + n_statistics)
        except:
            # log_current_exception()
            log.debug('Discarding error which may contain password')
            return True

    def no_schema(self, table=Constant):
        return super().no_schema(table=table)


def connect(args):
    '''
    Bootstrap from commandline-like args.
    '''
    from .config import Config
    if len(args) == 1 and isinstance(args[0], str):
        args = args[0].split()
    elif args:
        args = list(args)
    else:
        args = []
    args.append(NO_OP)
    ns = NamespaceWithVariables._from_ns(make_parser(with_noop=True).parse_args(args), PROGNAME, DB_VERSION)
    make_log_from_args(ns)
    data = Config(ns)
    return ns, data.db


class ReflectedDatabase(DatabaseBase):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)
