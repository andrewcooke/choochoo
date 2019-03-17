
import datetime as dt
from logging import getLogger

from ...lib.date import to_date, format_date
from ...lib.schedule import DOW, Schedule
from ...squeal.tables.topic import Topic
from ...squeal.utils import ORMUtils

log = getLogger(__name__)


class Assert:

    def _assert(self, value, msg):
        if not value:
            raise Exception(msg)


class Week(Assert, ORMUtils):

    def __init__(self, name=None, description=None, start=None, days=None):
        self.__name = name
        self.__description = description
        self.__start = to_date(start)
        self.__days = dict((key.lower(), value) for key, value in days.items())
        self.__n_weeks = max(len(day) for day in self.__days.values())
        self.__validate()

    def __validate(self):
        self._assert(self.__name, 'No name')
        self._assert(self.__description, 'No description')
        self._assert(self.__start, 'No start')
        self._assert(self.__days, 'No days')
        self._assert(self.__n_weeks, 'No notes defined in days')
        for key, day in self.__days.items():
            self._assert(key in DOW, 'Bad day: %s' % key)
            self._assert(len(day) == 0 or self.__n_weeks == len(day),
                         'Day %s of unusual length (%d/%d)' % (key, self.__n_weeks, len(day)))

    def create(self, db, parent='Plan', sort=10):
        with db.session_context() as s:
            parent = self.__create_parent(s, parent, sort)
            self.__create_children(s, parent, sort)

    def __create_parent(self, s, root, sort):
        if self.__start.weekday():
            log.warning('The start day (%s) is not a Monday, so the days will be rotated appropriately',
                     DOW[self.__start.weekday()])
        root = self._get_or_create(s, Topic, name=root)
        schedule = Schedule('')
        schedule.start = self.__start
        schedule.finish = self.__start + dt.timedelta(days=7 * self.__n_weeks)
        parent = Topic(parent=root, schedule=schedule, sort=sort,
                       name=self.__name, description=self.__description)
        s.add(parent)
        # extend root to include parent
        root.schedule = Schedule.include(root.schedule, parent.schedule)
        return parent

    def __create_children(self, s, parent, sort):
        date = self.__start
        for day in DOW:
            if day in self.__days:
                self.__days[day].create(s, parent, sort, date, self.__n_weeks)
            date += dt.timedelta(days=1)


class Day(Assert):

    def __init__(self, name=None, notes=None):
        self.__name = name
        self.__notes = notes if notes else []
        self._assert(self.__name, 'No name')

    def __len__(self):
        return len(self.__notes)

    def create(self, s, parent, sort, date, n_weeks):
        dow = date.weekday()
        schedule = Schedule('%s/w[%s]' % (format_date(date), DOW[dow]))
        schedule.start = date
        schedule.finish = date + dt.timedelta(days=7 * n_weeks)
        child = Topic(parent=parent, schedule=schedule, name=self.__name, sort=sort)
        s.add(child)
        for week, note in enumerate(self.__notes):
            diary = Topic(schedule=str(date + dt.timedelta(days=7 * week)), parent=child,
                          description=note)
            s.add(diary)
