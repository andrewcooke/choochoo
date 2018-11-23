
from collections import defaultdict

from sqlalchemy import func

from ..squeal.tables.constant import SystemConstant
from ..squeal.tables.statistic import StatisticJournal, StatisticName
from ..squeal.types import short_cls


class StatisticJournalLoader:
    '''
    Fast loading that requires locked access to the database (we pre-generate keys).
    '''

    def __init__(self, log, s, owner):
        self._log = log
        self._s = s
        self._owner = owner
        self.__statistic_name_cache = dict()
        self.__staging = defaultdict(lambda: [])
        self.__latest = dict()

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
        key = (name, constraint)
        if key not in self.__statistic_name_cache:
            self.__statistic_name_cache[key] = \
                StatisticName.add_if_missing(self._log, self._s, name, units, summary, self._owner, constraint)
        if key not in self.__statistic_name_cache or not self.__statistic_name_cache[key]:
            raise Exception('Failed to get StatisticName for %s' % key)
        if not self.__statistic_name_cache[key].id:
            self._s.flush()
            if not self.__statistic_name_cache[key].id:
                raise Exception('Could not get StatisticName.id for %s' % key)
        instance = type(statistic_name_id=self.__statistic_name_cache[key].id, source_id=source.id,
                        value=value, time=time)
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

