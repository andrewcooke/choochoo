
from sqlalchemy import desc, func, inspect, select, and_

from . import ActivityCalculator
from ..names import FTHR, HR_ZONE, HEART_RATE, BPM
from ..read.activity import ActivityImporter
from ...squeal.tables.constant import Constant
from ...squeal.tables.statistic import StatisticJournal, StatisticName, StatisticJournalFloat, StatisticJournalInteger


def hr_zones_from_database(log, s, activity_group, time):
    fthr = StatisticJournal.before(s, time, FTHR, Constant, activity_group)
    if fthr:
        return hr_zones(fthr.value)
    else:
        return None


def hr_zones(fthr):
    # values from british cycling online calculator
    # these are upper limits
    return [fthr * pc / 100.0 for pc in (68, 83, 94, 105, 121, 999)]


class HeartRateStatistics(ActivityCalculator):

    def __init__(self, log, db):
        self.__fthr_cache = None
        super().__init__(log, db)

    def _filter_journals(self, q):
        return q.filter(StatisticName.name == HR_ZONE)

    def _add_stats(self, s, ajournal):

        sjournals = []
        name = StatisticJournal.add_name(self._log, s, HR_ZONE, BPM, '[max],[avg]', self, ajournal.activity_group)
        rowid = s.query(func.max(StatisticJournal.id)).scalar() + 1

        sn = inspect(StatisticName).local_table
        sj = inspect(StatisticJournal).local_table
        sji = inspect(StatisticJournalInteger).local_table

        stmt = select([sj.c.time, sji.c.value]). \
            select_from(sj.join(sn).join(sji)). \
            where(and_(sj.c.source_id == ajournal.id,
                       sn.c.owner == ActivityImporter,
                       sn.c.name == HEART_RATE))
        # self._log.debug(stmt)

        for time, heart_rate in s.connection().execute(stmt):
            if heart_rate:
                heart_rate_zone = self._calculate_zone(s, heart_rate, time, ajournal.activity_group)
                if heart_rate_zone is not None:
                    sjournals.append(StatisticJournalFloat(id=rowid, value=heart_rate_zone,
                                                           statistic_name_id=name.id,
                                                           source_id=ajournal.id, time=time))
                    rowid += 1
        s.bulk_save_objects(sjournals)
        s.commit()
        self._log.debug('Added %d statistics' % len(sjournals))

    def _calculate_zone(self, s, hr, time, activity_group):
        self._load_fthr_cache(s, activity_group)
        for fthr in self.__fthr_cache:
            if fthr.time <= time:
                lower_limit, prev_delta = 0, None
                zones = hr_zones(fthr.value)
                for zone, upper_limit in enumerate(zones):
                    if lower_limit <= hr < upper_limit:
                        if zone == 0:
                            return 1 + zone
                        elif zone == 5:
                            return 1 + zone + (hr - lower_limit) / prev_delta
                        else:
                            return 1 + zone + (hr - lower_limit) / (upper_limit - lower_limit)
                    prev_delta = upper_limit - lower_limit
                    lower_limit = upper_limit

    def _load_fthr_cache(self, s, activity_group):
        if self.__fthr_cache is None:
            self.__fthr_cache = list(s.query(StatisticJournal).join(StatisticName).
                                     filter(StatisticName.name == FTHR,
                                            StatisticName.owner == Constant,
                                            StatisticName.constraint == activity_group).
                                     order_by(desc(StatisticJournal.time)).all())

    # todo - faster deletion
    # todo - impulse with gamma, min, max and scale