
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .support import Base
from .tables.activity import ActivityWaypoint, Activity, ActivityTimespan, ActivityJournal
from .tables.statistic import Statistic
from .tables.summary import RankingStatistic, DistributionStatistic, SummaryTimespan, Summary
from .tables.diary import DailyDiary
from .tables.zone import HeartRateZones, HeartRateZone
from .tables.injury import InjuryDiary, Injury
from .tables.topic import TopicJournal, Topic, TopicGroup
from ..args import DATABASE

# import these so they are "created"
DailyDiary, Injury, InjuryDiary, TopicGroup, Topic, TopicJournal,
Activity, ActivityJournal, ActivityWaypoint, ActivityTimespan, Statistic,
Summary, SummaryTimespan, RankingStatistic, DistributionStatistic,
HeartRateZones, HeartRateZone


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

