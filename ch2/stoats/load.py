
from collections import defaultdict

from sqlalchemy import func

from ..squeal.tables.statistic import StatisticJournal, StatisticName
from ..squeal.types import short_cls


class Loader:

    def __init__(self, log, s, owner):
        self._log = log
        self._s = s
        self._owner = owner
        self.__statistic_name_cache = dict()
        self.__staging = defaultdict(lambda: [])

    def __bool__(self):
        return bool(self.__staging)

    def load(self):
        # todo - database locking
        self._s.commit()
        rowid = self._s.query(func.max(StatisticJournal.id)).scalar() + 1
        for type in self.__staging:
            self._log.debug('Loading %d values for type %s' % (len(self.__staging[type]), short_cls(type)))
            for sjournal in self.__staging[type]:
                sjournal.id = rowid
                rowid += 1
            self._s.bulk_save_objects(self.__staging[type])

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
        self.__staging[type].append(
            type(statistic_name_id=self.__statistic_name_cache[key].id, source_id=source.id, value=value, time=time))
