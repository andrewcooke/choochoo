
import datetime as dt
from collections import namedtuple
from json import loads
from logging import getLogger

from sqlalchemy import desc, inspect, select, and_

from ch2.data import hr_zones
from . import MultiProcCalculator, ActivityJournalCalculatorMixin, DirectCalculatorMixin
from ..load import StatisticJournalLoader
from ..names import FTHR, HR_ZONE, HEART_RATE, S
from ...squeal import Constant, StatisticJournal, StatisticName, StatisticJournalFloat, StatisticJournalInteger, \
    ActivityGroup

log = getLogger(__name__)

# constraint comes from constant
HRImpulse = namedtuple('HRImpulse', 'dest_name, gamma, zero, max_secs')


class HeartRateCalculator(ActivityJournalCalculatorMixin, DirectCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, impulse=None, **kargs):
        self.impulse = self._assert('impulse', impulse)
        super().__init__(*args, **kargs)

    def _startup(self, s):
        self.__fthr_cache = {}
        for activity_group in s.query(ActivityGroup).all():
            self.__fthr_cache[activity_group.id] = \
                list(s.query(StatisticJournal).join(StatisticName).
                     filter(StatisticName.name == FTHR,
                            StatisticName.owner == Constant,
                            StatisticName.constraint == activity_group).
                     order_by(desc(StatisticJournal.time)).all())

    def _read_data(self, s, ajournal):
        sn = inspect(StatisticName).local_table
        sj = inspect(StatisticJournal).local_table
        sji = inspect(StatisticJournalInteger).local_table
        stmt = select([sj.c.time, sji.c.value]). \
            select_from(sj.join(sn).join(sji)). \
            where(and_(sj.c.source_id == ajournal.id,
                       sn.c.owner == self.owner_in,
                       sn.c.constraint == ajournal.activity_group,
                       sn.c.name == HEART_RATE)). \
            order_by(sj.c.time)
        # log.debug(stmt)
        return list(s.connection().execute(stmt))

    def _calculate_results(self, s, ajournal, data, loader):

        hr_impulse = HRImpulse(**loads(Constant.get(s, self.impulse).at(s).value))
        log.debug('%s: %s' % (self.impulse, hr_impulse))
        impulses = []
        prev_time, prev_heart_rate_zone = None, None

        for time, heart_rate in data:
            if heart_rate:
                heart_rate_zone = self._calculate_zone(s, heart_rate, time, ajournal.activity_group)
                if heart_rate_zone is not None:
                    loader.add(HR_ZONE, None, None, ajournal.activity_group, ajournal, heart_rate_zone, time,
                               StatisticJournalFloat)
            else:
                heart_rate_zone = None
            if prev_heart_rate_zone is not None:
                duration = (time - prev_time).total_seconds()
                if duration <= hr_impulse.max_secs:
                    heart_rate_impulse = self._calculate_impulse(prev_heart_rate_zone, duration, hr_impulse)
                    impulses.append((heart_rate_impulse, time))
                    loader.add(hr_impulse.dest_name, None, None, ajournal.activity_group, ajournal,
                               heart_rate_impulse, time, StatisticJournalFloat)
                    loader.add('%s (duration)' % hr_impulse.dest_name, S, None, ajournal.activity_group, ajournal,
                               duration, time, StatisticJournalFloat)
            elif not impulses:
                impulses.append((0, time))
            prev_time, prev_heart_rate_zone = time, heart_rate_zone

        if impulses:
            loader = StatisticJournalLoader(s, self)
            self._interpolate(hr_impulse.dest_name, loader, impulses, ajournal)
            # if there are no values, add a single null so we don't re-process
            if not loader:
                loader.add(HR_ZONE, None, None, ajournal.activity_group, ajournal, None, ajournal.start,
                           StatisticJournalFloat)
            loader.load()

    def _calculate_impulse(self, heart_rate_zone, duration, hr_impulse):
        return duration * ((max(heart_rate_zone, hr_impulse.zero) - hr_impulse.zero)
                           / (6 - hr_impulse.zero)) ** hr_impulse.gamma

    def _calculate_zone(self, s, heart_rate, time, activity_group):
        for fthr in self.__fthr_cache[activity_group.id]:
            if fthr.time <= time:  # ordered in descending time
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

    def _interpolate(self, name, loader, impulses, ajournal, interval=10):

        # we need evenly-sampled statistics so we can do distributions over time.
        # why interpolate just this one statistic?
        # because it's not the same as others - it's already time-based
        # so interpolating it later is more complex.
        # but i may change my mind

        # you can configure names, but plotting assumes HR_IMPULSE_10 exists...

        integral, sum = [], 0
        for impulse, time in impulses:
            sum += impulse
            integral.append((sum, time))

        impulse_0, time_0 = integral.pop(0)
        time, prev = time_0, 0
        while integral:
            impulse_1, time_1 = integral[0]
            delta = (time_1 - time_0).total_seconds()
            while time <= time_1:
                interp = impulse_0 + (impulse_1 - impulse_0) * (time - time_0).total_seconds() / delta
                diff = (interp - prev) / interval
                loader.add(f'{name} / {interval}s', None, None, ajournal.activity_group, ajournal, diff, time,
                           StatisticJournalFloat)
                time += dt.timedelta(seconds=interval)
                prev = interp
            while integral and time > integral[0][1]:
                impulse_0, time_0 = integral.pop(0)
