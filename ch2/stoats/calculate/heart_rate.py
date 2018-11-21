from json import loads

from sqlalchemy import desc, func, inspect, select, and_

from ch2.stoats.load import Loader
from . import ActivityCalculator
from .impulse import HRImpulse
from ..names import FTHR, HR_ZONE, HEART_RATE
from ..read.activity import ActivityImporter
from ...squeal.tables.activity import ActivityGroup
from ...squeal.tables.constant import Constant
from ...squeal.tables.statistic import StatisticJournal, StatisticName, StatisticJournalFloat, StatisticJournalInteger
from ...squeal.types import short_cls


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
        # must create the statistic(s) before finding out if it is missing...
        with db.session_context() as s:
            for agroup in s.query(ActivityGroup).all():
                StatisticName.add_if_missing(log, s, HR_ZONE, None, None, self, agroup)
        super().__init__(log, db)

    def _filter_journals(self, q):
        return q.filter(StatisticName.name == HR_ZONE)

    def _add_stats(self, s, ajournal, impulse=None):

        if not impulse:
            raise Exception('Missing impulse karg for %s' % short_cls(self))
        hr_impulse = HRImpulse(**loads(Constant.get(s, impulse).at(s).value))
        self._log.debug('%s: %s' % (impulse, hr_impulse))

        loader = Loader(self._log, s, self)

        sn = inspect(StatisticName).local_table
        sj = inspect(StatisticJournal).local_table
        sji = inspect(StatisticJournalInteger).local_table

        stmt = select([sj.c.time, sji.c.value]). \
            select_from(sj.join(sn).join(sji)). \
            where(and_(sj.c.source_id == ajournal.id,
                       sn.c.owner == ActivityImporter,
                       sn.c.constraint == ajournal.activity_group,
                       sn.c.name == HEART_RATE)). \
            order_by(sj.c.time)
        # self._log.debug(stmt)

        prev_time, prev_heart_rate_zone = None, None
        for time, heart_rate in s.connection().execute(stmt):
            if heart_rate:
                heart_rate_zone = self._calculate_zone(s, heart_rate, time, ajournal.activity_group)
                if heart_rate_zone is not None:
                    loader.add(HR_ZONE, None, None, ajournal.activity_group, ajournal, heart_rate_zone, time,
                               StatisticJournalFloat)
            else:
                heart_rate_zone = None
            if prev_heart_rate_zone is not None:
                heart_rate_impulse = self._calculate_impulse(prev_heart_rate_zone, time - prev_time, hr_impulse)
                loader.add(hr_impulse.dest_name, None, None, ajournal.activity_group, ajournal, heart_rate_impulse,
                           time, StatisticJournalFloat)
            prev_time, prev_heart_rate_zone = time, heart_rate_zone

        # if there are no values, add a single null so we don't re-process
        if not loader:
            loader.add(HR_ZONE, None, None, ajournal.activity_group, ajournal, None, ajournal.start,
                       StatisticJournalFloat)

        loader.load()
        s.commit()

    def _calculate_impulse(self, heart_rate_zone, duration, hr_impulse):
        return duration.total_seconds() * \
               ((max(heart_rate_zone, hr_impulse.zero) - hr_impulse.zero)
                / (6 - hr_impulse.zero)) ** hr_impulse.gamma

    def _calculate_zone(self, s, heart_rate, time, activity_group):
        self._load_fthr_cache(s, activity_group)
        for fthr in self.__fthr_cache:
            if fthr.time <= time:
                lower_limit, prev_delta = 0, None
                zones = hr_zones(fthr.value)
                for zone, upper_limit in enumerate(zones):
                    if lower_limit <= heart_rate < upper_limit:
                        if zone == 0:
                            return 1 + zone
                        elif zone == 5:
                            return 1 + zone + (heart_rate - lower_limit) / prev_delta
                        else:
                            return 1 + zone + (heart_rate - lower_limit) / (upper_limit - lower_limit)
                    prev_delta = upper_limit - lower_limit
                    lower_limit = upper_limit

    def _load_fthr_cache(self, s, activity_group):
        if self.__fthr_cache is None:
            self.__fthr_cache = list(s.query(StatisticJournal).join(StatisticName).
                                     filter(StatisticName.name == FTHR,
                                            StatisticName.owner == Constant,
                                            StatisticName.constraint == activity_group).
                                     order_by(desc(StatisticJournal.time)).all())

