
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .diary import Diary
from .injury import InjuryDiary, Injury
from .schedule import ScheduleDiary, Schedule, ScheduleType
from .support import Base
from ..args import DATABASE


# import these so they are "created"
Diary, Injury, InjuryDiary, ScheduleType, Schedule, ScheduleDiary


class Database:

    def __init__(self, args, log):
        self._log = log
        path = args.file(DATABASE)
        self._log.info('Using database at %s' % path)
        self.engine = create_engine('sqlite:///%s' % path, echo=True)
        self.__create_tables()
        self.session = sessionmaker(bind=self.engine)

    def __create_tables(self):
        self._log.info('Creating tables')
        Base.metadata.create_all(self.engine)
