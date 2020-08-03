from abc import ABC
from collections import defaultdict, namedtuple
from logging import getLogger

from ..common.date import min_time, max_time
from ..common.math import is_nan
from ..names import simple_name
from ..sql import StatisticName, Interval, Source
from ..sql.tables.statistic import STATISTIC_JOURNAL_CLASSES, STATISTIC_JOURNAL_TYPES

log = getLogger(__name__)


class Loader(ABC):

    def __init__(self, s, owner, add_serial=True, clear_timestamp=True, batch=True):
        self._s = s
        self._owner = owner
        self.__serial = 0 if add_serial else None
        self.__clear_timestamp = clear_timestamp
        self.__batch = batch

        self.__statistic_name_cache = dict()
        self.__source_cache = dict()
        self._staging = defaultdict(list)
        self.__by_name_then_time = defaultdict(dict)
        self.__add_serial = add_serial
        self._start = None
        self._finish = None
        self.__last_time = None
        self.__counts = defaultdict(lambda: 0)

    def load(self):
        if self:
            for type in self._staging:
                log.debug(f'Adding {len(self._staging[type])} instances of {type}')
                for instance in self._staging[type]:
                    self._s.add(instance)
                self._s.commit()
            self._postload()
        else:
            log.warning('No data to load')

    def __bool__(self):
        return bool(self._staging)

    def _postload(self):
        # manually clean out intervals because we're doing a fast load
        if self.__clear_timestamp and self._start and self._finish:
            Interval.record_dirty_times(self._s, self._start, self._finish)
            self._s.commit()

    def add(self, name, units, summary, source, value, time, cls, description=None, title=None):
        # note that name is used as title if title is None, and name is reduced to a simple name.
        # so legacy code works correctly
        title = title or name
        name = simple_name(name)
        if name not in self.__statistic_name_cache:
            if not description: log.warning(f'No description for {name} ({self._owner})')
            self.__statistic_name_cache[name] = \
                StatisticName.add_if_missing(self._s, name, STATISTIC_JOURNAL_TYPES[cls],
                                             units, summary, self._owner,
                                             description=description, title=title)
        statistic_name = self.__statistic_name_cache[name]
        journal_class = STATISTIC_JOURNAL_CLASSES[statistic_name.statistic_journal_type]
        if cls != journal_class:
            raise Exception(f'Inconsistent class for {name}: {cls}/{journal_class}')

        self.__add_internal(statistic_name, source, value, time)

    def add_data_only(self, name, source, value, time):
        if name in self.__statistic_name_cache:
            statistic_name = self.__statistic_name_cache[name]
        else:
            statistic_name = StatisticName.from_name(self._s, name, self._owner)
            self.__statistic_name_cache[name] = statistic_name
        self.__add_internal(statistic_name, source, value, time)

    def __add_internal(self, statistic_name, source, value, time):

        if value is None or is_nan(value):
            raise Exception(f'Bad value for {statistic_name.name}: {value}')

        journal_class = STATISTIC_JOURNAL_CLASSES[statistic_name.statistic_journal_type]

        if self.__add_serial:
            if self.__last_time is None:
                self.__last_time = time
            elif time > self.__last_time:
                self.__last_time = time
                self.__serial += 1
            elif time < self.__last_time:
                raise Exception('Time travel - timestamp for statistic decreased')

        if isinstance(source, Source):
            if source.id not in self.__source_cache:
                self.__source_cache[source.id] = source
        else:
            if source not in self.__source_cache:
                self.__source_cache[source] = Source.from_id(self._s, source)
            source = self.__source_cache[source]

        self._start = min_time(self._start, time)
        self._finish = max_time(self._finish, time)

        # set statistic_name and source (as well as ids) so that we can correctly test in
        # Source for dirty intervals
        instance = journal_class(statistic_name=statistic_name, statistic_name_id=statistic_name.id,
                                 source=source, source_id=source.id, value=value, time=time, serial=self.__serial)

        if instance.time in self.__by_name_then_time[statistic_name.name]:
            previous = self.__by_name_then_time[statistic_name.name][instance.time]
            if instance.value == previous.value:
                log.warning(f'Discarding duplicate for {statistic_name.name} at {instance.time} '
                            f'(value {instance.value})')
            else:
                self._resolve_duplicate(statistic_name.name, instance, previous)
            return
        else:
            self.__by_name_then_time[statistic_name.name][instance.time] = instance

        self._staging[journal_class].append(instance)
        self.__counts[statistic_name.name] += 1

    def _resolve_duplicate(self, name, instance, prev):
        raise Exception(f'Conflict at ({instance.time}) for {name} '
                        f'(values {instance.value}/{prev.value})')

    def as_waypoints(self, names):
        Waypoint = make_waypoint(names.values())
        time_to_waypoint = defaultdict(lambda: Waypoint())
        for type in self._staging:
            for sjournal in self._staging[type]:
                name = sjournal.statistic_name.name
                if name in names:
                    time_to_waypoint[sjournal.time] = \
                        time_to_waypoint[sjournal.time]._replace(**{'time': sjournal.time,
                                                                    names[name]: sjournal.value})
        return [time_to_waypoint[time] for time in sorted(time_to_waypoint.keys())]

    def coverage_percentages(self):
        total = max(self.__counts.values())
        for name, count in self.__counts.items():
            yield name, 100 * count / total


def make_waypoint(names, extra=None):
    names = list(names)
    if extra:
        names += [extra]
    names = ['time'] + names
    defaults = [None] * len(names)
    return namedtuple('Waypoint', names, defaults=defaults)
