from abc import ABC, abstractmethod
from collections import defaultdict, namedtuple
from logging import getLogger
from time import sleep

from sqlalchemy.exc import IntegrityError
from sqlalchemy_batch_inserts import enable_batch_inserting

from ..commands.args import UNLOCK
from ..sql import StatisticJournal, StatisticName, Dummy, Interval
from ..sql.tables.statistic import STATISTIC_JOURNAL_CLASSES, STATISTIC_JOURNAL_TYPES
from ..sql.types import short_cls

log = getLogger(__name__)


class BaseLoader(ABC):

    def __init__(self, s, owner, add_serial=True, clear_timestamp=True):
        self._s = s
        self._owner = owner
        self.__statistic_name_cache = dict()
        self._staging = defaultdict(list)
        self.__by_name_then_time = defaultdict(dict)
        self.__add_serial = add_serial
        self._start = None
        self._finish = None
        self.__last_time = None
        self.__serial = 0 if add_serial else None
        self.__clear_timestamp = clear_timestamp
        self.__counts = defaultdict(lambda: 0)

    def __bool__(self):
        return bool(self._staging)

    @abstractmethod
    def load(self):
        # should call postload on success
        raise NotImplementedError(f'{self.__class__.__name__}.load')

    def _postload(self):
        # manually clean out intervals because we're doing a fast load
        if self.__clear_timestamp and self._start and self._finish:
            Interval.mark_dirty_times(self._s, self._start, self._finish)
            self._s.commit()

    def add(self, name, units, summary, source, value, time, cls, description=None, title=None):
        # note that name is used as title if title is None, and name is reduced to a simple name.
        # so legacy code works correctly

        if value is None or value != value:
            raise Exception(f'Bad value for {name}: {value}')

        if self.__add_serial:
            if self.__last_time is None:
                self.__last_time = time
            elif time > self.__last_time:
                self.__last_time = time
                self.__serial += 1
            elif time < self.__last_time:
                raise Exception('Time travel - timestamp for statistic decreased')

        self._start = min(self._start, time) if self._start else time
        self._finish = max(self._finish, time) if self._finish else time

        if name not in self.__statistic_name_cache:
            if not description: log.warning(f'No description for {name} ({self._owner})')
            self.__statistic_name_cache[name] = \
                StatisticName.add_if_missing(self._s, name, STATISTIC_JOURNAL_TYPES[cls],
                                             units, summary, self._owner,
                                             description=description, title=title)

        try:
            source = source.id
        except AttributeError:
            pass  # literal id
        statistic_name = self.__statistic_name_cache[name]
        journal_class = STATISTIC_JOURNAL_CLASSES[statistic_name.statistic_journal_type]
        if cls != journal_class:
            raise Exception(f'Inconsistent class for {name}: {cls}/{journal_class}')
        instance = journal_class(statistic_name_id=statistic_name.id, source_id=source, value=value,
                                 time=time, serial=self.__serial)

        if instance.time in self.__by_name_then_time[name]:
            previous = self.__by_name_then_time[name][instance.time]
            if instance.value == previous.value:
                log.warning(f'Discarding duplicate for {name} at {instance.time} (value {instance.value})')
            else:
                self._resolve_duplicate(name, instance, previous)
            return
        else:
            self.__by_name_then_time[name][instance.time] = instance

        self._staging[journal_class].append(instance)
        self.__counts[name] += 1

    def _resolve_duplicate(self, name, instance, prev):
        raise Exception(f'Conflict at ({instance.time}) for {name} '
                        f'(values {instance.value}/{prev.value})')

    def as_waypoints(self, names):
        Waypoint = make_waypoint(names.values())
        time_to_waypoint = defaultdict(lambda: Waypoint())
        statistic_ids = dict((name.id, name) for name in self.__statistic_name_cache.values())
        for type in self._staging:
            for sjournal in self._staging[type]:
                name = statistic_ids[sjournal.statistic_name_id].name
                if name in names:
                    time_to_waypoint[sjournal.time] = \
                        time_to_waypoint[sjournal.time]._replace(**{'time': sjournal.time,
                                                                    names[name]: sjournal.value})
        return [time_to_waypoint[time] for time in sorted(time_to_waypoint.keys())]

    def coverage_percentages(self):
        total = max(self.__counts.values())
        for name, count in self.__counts.items():
            yield name, 100 * count / total


class SqliteLoader(BaseLoader):

    # we want to load multiple tables (because we're using inheritance) quickly and safely.
    # to do this, we need to generate IDs ourselves (to avoid reading the ID for the base class)
    # on sqlite we can do this by:
    # - using a single transaction
    # - starting to write (a dummy StatisticJournal, which also gets us the last ID)
    # - calculating IDs from the dummy ID
    # - writing the data (still in the same transaction)
    # - removing the dummy
    # - committing
    # afaict that would work on any SQL database with a reasonable level of isolation.
    # what is special to sqlite is that the final commit will not fail, because there is only ever one
    # process writing (this is true even when using multiple processes)

    # well the above worked for a while. then started throwing exceptions, so i needed to add
    # the while loop below.

    def __init__(self, s, owner, add_serial=True, clear_timestamp=True, abort_after=100):
        super().__init__(s, owner, add_serial=add_serial, clear_timestamp=clear_timestamp)
        self.__abort_after = abort_after

    def load(self):
        if not self:
            log.warning('No data to load')
            return
        self._s.commit()
        dummy = self._preload()
        try:
            self._load_ids(dummy)
        except Exception:
            self._s.rollback()
            # dummy may have been deleted in the rollback - it depends if there were any intermediate commits
            # (which is a whole other problem), so to be sure...
            self.unlock(self._s)
            raise
        self._postload()

    def _preload(self):
        dummy_source, dummy_name = Dummy.singletons(self._s)
        dummy, count = None, 0
        while not dummy:
            try:
                log.debug(f'Trying to acquire database ({count})')
                dummy = StatisticJournal(source=dummy_source, statistic_name=dummy_name, time=0.0)
                self._s.add(dummy)
                self._s.flush()
                log.debug('Acquired database')
            except IntegrityError:
                log.debug('Failed to acquire database')
                self._s.rollback()
                dummy, count = None, count+1
                if count > self.__abort_after:
                    raise Exception(f'Could not acquire database after {count} attempts '
                                    f'(you may need to use `ch2 {UNLOCK}` once all workers have stopped)')
                sleep(0.1)
        log.debug(f'Dummy ID {dummy.id}')
        return dummy

    def _load_ids(self, dummy):
        rowid, count = dummy.id + 1, 0
        for type in self._staging:
            log.debug('Loading %d values for type %s' % (len(self._staging[type]), short_cls(type)))
            for i in range(min(5, len(self._staging[type]))):
                sjournal = self._staging[type][i]
                log.debug(f'Example: {sjournal.value} at {sjournal.time}')
            for sjournal in self._staging[type]:
                sjournal.id = rowid
                rowid += 1
            self._s.bulk_save_objects(self._staging[type])
            count += len(self._staging[type])
        self._s.commit()
        log.info(f'Loaded {count} statistics')
        log.debug('Removing Dummy')
        self._s.delete(dummy)
        self._s.commit()
        log.debug('Dummy removed')

    @classmethod
    def unlock(cls, s):
        dummy_source, dummy_name = Dummy.singletons(s)
        s.query(StatisticJournal). \
            filter(StatisticJournal.source == dummy_source,
                   StatisticJournal.statistic_name == dummy_name).delete()
        s.commit()


def make_waypoint(names, extra=None):
    names = list(names)
    if extra:
        names += [extra]
    names = ['time'] + names
    defaults = [None] * len(names)
    return namedtuple('Waypoint', names, defaults=defaults)


class PostgresqlLoader(BaseLoader):

    def __init__(self, s, owner, add_serial=True, clear_timestamp=True, **kargs):
        super().__init__(s, owner, add_serial=add_serial, clear_timestamp=clear_timestamp)
        if kargs: log.debug(f'Ignoring {kargs}')

    def load(self):
        if self:
            enable_batch_inserting(self._s)
            for type in self._staging:
                log.debug(f'Adding {len(self._staging[type])} instances of {type}')
                for instance in self._staging[type]:
                    self._s.add(instance)
                self._s.commit()
            self._postload()
        else:
            log.warning('No data to load')
