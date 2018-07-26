
from ..squeal.schedule import ScheduleType, Schedule, ScheduleDiary
from .utils import ORMUtils
from ..lib.date import parse_duration, duration_to_secs, parse_date, add_duration, format_duration
from ..lib.repeating import Specification


class Builder(ORMUtils):

    def __init__(self, title, description, spec, time, ratio):
        self._title = title
        self._description = description
        self._spec = spec
        self.__time = time
        self._ratio = ratio

    def create(self, log, session):
        type = self._get_or_create(session, ScheduleType, name='Plan')
        schedule = Schedule(type=type, repeat=str(self._spec), start=self._spec.start, finish=self._spec.finish,
                            title=self._title, description=self._description, has_notes=True)
        session.add(schedule)
        for day in self._spec.frame().dates(self._spec.start):
            session.add(ScheduleDiary(date=day, schedule=schedule, notes=format_duration(self.__time)))
            self.__time *= self._ratio


def exponential_time(title, repeat, time, percent, start, duration):
    """
    A time interval that increases steadily by a given percentage.
    Takes 6 arguments: title, repeat spec, initial time, percent increase,
                       start date, duration
    Example:

      ch2 plan percent-time 'Run duration' 'w[mon,wed,fri]' 20m 10 2018-07-20 1M

      where 20m is the 20 minute initial time, 1M generates plans over a
      month, and w[mon,wed,fri] indicates which days of each week.
    """
    time_s = duration_to_secs(parse_duration(time))
    ratio = 1 + float(percent) / 100.0
    spec = Specification(start + "/" + repeat)
    start = parse_date(start)
    finish = add_duration(start, parse_duration(duration))
    spec.start = start
    spec.finish = finish
    return Builder(title, 'Time starting at %s and incrementing by %s%%' % (time, percent),
                   spec, time_s, ratio)
