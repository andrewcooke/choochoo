
from collections import defaultdict

from sqlalchemy import func

from .waypoint import make_waypoint
from ..squeal import StatisticJournal, StatisticName, SystemConstant
from ..squeal.types import short_cls


class StatisticJournalLoader:
    '''
    Fast loading that requires locked access to the database (we pre-generate keys).
    '''

    def __init__(self, log, s, owner, add_serial=True):
        self._log = log
        self._s = s
        self._owner = owner
        self.__statistic_name_cache = dict()
        self.__staging = defaultdict(lambda: [])
        self.__latest = dict()
        self.__add_serial = add_serial
        self.__last_time = None
        self.__serial = 0 if add_serial else None

    def __bool__(self):
        return bool(self.__staging)

    def load(self):
        SystemConstant.acquire_lock(self._s, self)  # includes flush so query below OK
        try:
            rowid = self._s.query(func.max(StatisticJournal.id)).scalar() + 1
            for type in self.__staging:
                self._log.debug('Loading %d values for type %s' % (len(self.__staging[type]), short_cls(type)))
                for sjournal in self.__staging[type]:
                    sjournal.id = rowid
                    rowid += 1
                self._s.bulk_save_objects(self.__staging[type])
        finally:
            SystemConstant.release_lock(self._s, self)

    def add(self, name, units, summary, constraint, source, value, time, type):

        if self.__add_serial:
            if self.__last_time is None:
                self.__last_time = time
            elif time > self.__last_time:
                self.__last_time = time
                self.__serial += 1
            elif time < self.__last_time:
                raise Exception('Time travel!')

        key = (name, constraint)
        if key not in self.__statistic_name_cache:
            self.__statistic_name_cache[key] = \
                StatisticName.add_if_missing(self._log, self._s, name, units, summary, self._owner, constraint)
        if not self.__statistic_name_cache.get(key, None):
            raise Exception('Failed to get StatisticName for %s' % key)
        if not self.__statistic_name_cache[key].id:
            self._s.flush()
            if not self.__statistic_name_cache[key].id:
                raise Exception('Could not get StatisticName.id for %s' % key)

        instance = type(statistic_name_id=self.__statistic_name_cache[key].id, source_id=source.id,
                        value=value, time=time, serial=self.__serial)
        self.__staging[type].append(instance)
        if key in self.__latest:
            prev = self.__latest[key]
            if instance.time > prev.time:
                self.__latest[key] = instance
        else:
            self.__latest[key] = instance

    def latest(self, name, constraint, instance=None):
        latest = self.__latest.get((name, constraint))
        if latest:
            if instance and instance.time > latest.time:
                latest = instance
        else:
            latest = instance
        return latest

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
