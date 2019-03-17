
from collections import defaultdict
from logging import getLogger
from time import time, sleep

from sqlalchemy.exc import IntegrityError

from .waypoint import make_waypoint
from ..squeal import StatisticJournal, StatisticName, Dummy, Interval
from ..squeal.types import short_cls


log = getLogger(__name__)


class StatisticJournalLoader:

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
        self._s = s
        self._owner = owner
        self.__statistic_name_cache = dict()
        self.__staging = defaultdict(lambda: [])
        self.__latest = dict()
        self.__add_serial = add_serial
        self.__start = None
        self.__finish = None
        self.__last_time = None
        self.__serial = 0 if add_serial else None
        self.__clear_timestamp = clear_timestamp
        self.__abort_after = abort_after

    def __bool__(self):
        return bool(self.__staging)

    def load(self):
        self._s.commit()
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
                    raise Exception(f'Could not acquire database after {count} attempts')
                sleep(0.1)
        log.debug(f'Dummy ID {dummy.id}')
        try:
            rowid = dummy.id + 1
            for type in self.__staging:
                log.debug('Loading %d values for type %s' % (len(self.__staging[type]), short_cls(type)))
                for sjournal in self.__staging[type]:
                    sjournal.id = rowid
                    rowid += 1
                self._s.bulk_save_objects(self.__staging[type])
            self._s.commit()
        except Exception:
            self._s.rollback()
            raise
        finally:
            log.debug('Removing Dummy')
            self._s.delete(dummy)
            self._s.commit()
            log.debug('Dummy removed')

        # manually clean out intervals because we're doing a fast load
        if self.__clear_timestamp and self.__start and self.__finish:
            Interval.clean_times(log, self._s, self.__start, self.__finish)
            self._s.commit()

    def add(self, name, units, summary, constraint, source, value, time, type):

        if self.__add_serial:
            if self.__last_time is None:
                self.__last_time = time
            elif time > self.__last_time:
                self.__last_time = time
                self.__serial += 1
            elif time < self.__last_time:
                raise Exception('Time travel!')

        self.__start = min(self.__start, time) if self.__start else time
        self.__finish = max(self.__finish, time) if self.__finish else time

        key = (name, constraint)
        if key not in self.__statistic_name_cache:
            self.__statistic_name_cache[key] = \
                StatisticName.add_if_missing(log, self._s, name, units, summary, self._owner, constraint)

        instance = type(statistic_name_id=self.__statistic_name_cache[key].id, source_id=source.id,
                        value=value, time=time, serial=self.__serial)
        self.__staging[type].append(instance)
        if key in self.__latest:
            prev = self.__latest[key]
            if instance.time > prev.time:
                self.__latest[key] = instance
        else:
            self.__latest[key] = instance

    def latest(self, name, constraint):
        return self.__latest.get((name, constraint))

    def as_waypoints(self, names):
        Waypoint = make_waypoint(names.values())
        time_to_waypoint = defaultdict(lambda: Waypoint())
        statistic_ids = dict((name.id, name) for name in self.__statistic_name_cache.values())
        for type in self.__staging:
            for sjournal in self.__staging[type]:
                name = statistic_ids[sjournal.statistic_name_id].name
                if name in names:
                    time_to_waypoint[sjournal.time] = \
                        time_to_waypoint[sjournal.time]._replace(**{'time': sjournal.time,
                                                                    names[name]: sjournal.value})
        return [time_to_waypoint[time] for time in sorted(time_to_waypoint.keys())]
