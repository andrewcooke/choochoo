
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.functions import count

from .support import Base
from .tables.activity import ActivityWaypoint, Activity, ActivityTimespan, ActivityJournal
from .tables.config import StatisticPipeline, DiaryPipeline
from .tables.source import Source, Interval
from .tables.statistic import Statistic, StatisticJournalFloat, StatisticJournalText, StatisticJournalInteger, \
    StatisticJournal
from .tables.topic import TopicJournal, Topic
from ..command.args import DATABASE

# import these so they are "created"
Source,  Interval,
Activity, ActivityJournal, ActivityTimespan, ActivityWaypoint,
Topic, TopicJournal,
Statistic, StatisticJournal, StatisticJournalInteger, StatisticJournalFloat, StatisticJournalText,
StatisticPipeline, DiaryPipeline


# https://stackoverflow.com/questions/13712381/how-to-turn-on-pragma-foreign-keys-on-in-sqlalchemy-migration-script-or-conf
@event.listens_for(Engine, "connect")
def fk_pragma_on_connect(dbapi_con, _con_record):
    cursor = dbapi_con.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
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
                n_activities = s.query(count(Activity.id)).scalar()
                n_statistics = s.query(count(Statistic.id)).scalar()
            return not (n_topics + n_activities + n_statistics)


def add(s, instance):
    s.add(instance)
    return instance
