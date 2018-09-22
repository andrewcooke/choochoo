
import datetime as dt

from sqlalchemy import or_

from ..lib.date import parse_date, format_date
from ..lib.repeating import DOW
from ..squeal.tables.schedule import ScheduleGroup, Schedule, ScheduleDiary
from ..squeal.utils import ORMUtils


class Assert:

    def _assert(self, value, msg):
        if not value:
            raise Exception(msg)


class Week(Assert, ORMUtils):

    def __init__(self, name=None, description=None, start=None, days=None):
        self.__name = name
        self.__description = description
        self.__start = parse_date(start)
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

    def create(self, log, session):
        root = self.__create_root(log, session)
        self.__create_children(log, session, root)

    def __create_root(self, log, session):
        if self.__start.weekday():
            log.warn('The start day (%s) is not a Monday, so the days will be rotated appropriately',
                     DOW[self.__start.weekday()])
        finish = self.__start + dt.timedelta(days=7 * self.__n_weeks)
        if session.query(Schedule).join(Schedule.group).filter(ScheduleGroup.name == 'Plan'). \
                filter(or_(Schedule.start <= finish, Schedule.start == None)). \
                filter(or_(Schedule.finish >= self.__start, Schedule.finish == None)).count():
            raise Exception('A training plan is already defined for this date range')
        type = self._get_or_create(session, ScheduleGroup, name='Plan')
        root = Schedule(type=type, repeat='', start=self.__start, finish=finish,
                        name=self.__name, description=self.__description, has_notes=False)
        session.add(root)
        return root

    def __create_children(self, log, session, root):
        date = self.__start
        for sort, day in enumerate(DOW):
            if day in self.__days:
                self.__days[day].create(log, session, root, sort, date, self.__n_weeks)
            date += dt.timedelta(days=1)


class Day(Assert):

    def __init__(self, name=None, notes=None):
        self.__name = name
        self.__notes = self.__expand(notes)
        self.__validate()

    def __validate(self):
        self._assert(self.__name, 'No name')

    def __len__(self):
        return len(self.__notes)

    def __expand(self, spec):
        if spec is None:
            return []
        else:
            return list(self.__unwind(spec))

    def __unwind(self, spec):
        n = 0
        try:
            if isinstance(spec[0], int):
                n, spec = spec[0], spec[1:]
        except TypeError:
            pass
        if n:
            for i in range(n):
                for x in self.__unwind(spec):
                    yield x
        elif spec is None:
            yield None
        elif isinstance(spec, str):
            yield spec
        else:
            for x in spec:
                for y in self.__unwind(x):
                    yield y

    def create(self, log, session, root, sort, date, n_weeks):
        dow = date.weekday()
        finish = date + dt.timedelta(days=7 * n_weeks)
        child = Schedule(parent=root, repeat='%s/w[%s]' % (format_date(date), DOW[dow]), start=date, finish=finish,
                         name=self.__name, has_notes=True, sort=str(sort))
        session.add(child)
        for week, note in enumerate(self.__notes):
            diary = ScheduleDiary(date=date + dt.timedelta(days=7 * week), schedule=child, notes=note)
            session.add(diary)
