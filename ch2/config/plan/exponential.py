
from abc import abstractmethod
from re import compile

from ...lib.date import format_seconds, to_date, add_date
from ...lib.schedule import Schedule
from ...squeal.tables.topic import Topic
from ...squeal.utils import ORMUtils


class Builder(ORMUtils):

    def __init__(self, name, description, spec, ratio):
        self._name = name
        self._description = description
        self._spec = spec
        self._ratio = ratio

    def create(self, db, parent='Plan', sort=10):
        with db.session_context() as s:
            root = self._get_or_create(s, Topic, name=parent, sort=sort)
            child = Topic(parent=root, schedule=self._spec,
                          name=self._name, description=self._description, sort=sort)
            s.add(child)
            root.schedule = Schedule.include(root.schedule, child.schedule)
            for day in self._spec.locations_from(self._spec.start):
                s.add(Topic(parent=child, schedule=str(day), name=self._next_value()))

    @abstractmethod
    def _next_value(self):
        pass


class TimeBuilder(Builder):

    def __init__(self, name, description, spec, time, ratio):
        self.__time = time
        super().__init__(name, description, spec, ratio)

    def _next_value(self):
        time = self.__time
        self.__time *= self._ratio
        return format_seconds(time)


class DistanceBuilder(Builder):

    def __init__(self, name, description, spec, distance, unit, ratio):
        self.__distance = distance
        self.__unit = unit
        super().__init__(name, description, spec, ratio)

    def _next_value(self):
        distance = self.__distance
        self.__distance *= self._ratio
        return '%.1f%s' % (distance, self.__unit)


def exponential_time(name, repeat, time, percent, start, duration):
    """
    A time interval that increases steadily by a given percentage.
    Takes 6 arguments: name, repeat spec, initial time, percent increase,
                       start date, duration
    """
    time_s = parse_time(time)
    ratio = 1 + float(percent) / 100.0
    spec = Schedule(start + "/" + repeat)
    start = to_date(start)
    finish = add_date(start, parse_duration(duration))
    spec.start = start
    spec.finish = finish
    return TimeBuilder(name, 'Time starting at %s and incrementing by %s%%' % (time, percent),
                       spec, time_s, ratio)


def exponential_distance(name, repeat, distance, percent, start, duration):
    """
    A distance that increases steadily by a given percentage.
    Takes 6 arguments: name, repeat spec, initial distance, percent increase,
                       start date, duration
    """
    match = compile(r'(\d+)(\D*)').match(distance)
    dist, unit = float(match.group(1)), match.group(2)
    ratio = 1 + float(percent) / 100.0
    spec = Schedule(start + "/" + repeat)
    start = to_date(start)
    finish = add_date(start, parse_duration(duration))
    spec.start = start
    spec.finish = finish
    return DistanceBuilder(name, 'Distance starting at %s and incrementing by %s%%' % (distance, percent),
                           spec, dist, unit, ratio)


def parse_time(time):
    '''
    Convert to seconds.  Supports h, m, s.
    '''
    try:
        return int(time)
    except:
        units, time = time[-1].lower(), int(time[:-1])
        return {'s': 1, 'm': 60, 'h': 60*60}[units] * time


def parse_duration(duration):
    '''
    Convert to duration used by lib.date.  Supports d, w, m, y
    '''
    try:
        return int(duration), 'd'
    except:
        units, duration = duration[-1].lower(), duration[:-1]
        if units in 'dwmy':
            return int(duration), units
        else:
            raise
