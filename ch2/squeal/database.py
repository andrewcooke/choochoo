
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .support import Base
from .tables.activity import ActivityWaypoint, Activity, ActivityTimespan, ActivityJournal
from .tables.source import Source, Interval
from .tables.statistic import Statistic, StatisticJournalFloat, StatisticJournalText, StatisticJournalInteger, \
    StatisticJournal, StatisticPipeline
from .tables.topic import TopicJournal, Topic
from ..command.args import DATABASE

# import these so they are "created"
Source,  Interval,
Activity, ActivityJournal, ActivityTimespan, ActivityWaypoint,
Topic, TopicJournal,
Statistic, StatisticJournal, StatisticJournalInteger, StatisticJournalFloat, StatisticJournalText, StatisticPipeline


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

