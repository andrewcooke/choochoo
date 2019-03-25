
from logging import getLogger

from sqlalchemy.sql import func

from . import IntervalCalculatorMixin, MultiProcCalculator
from ..names import STEPS, REST_HR, HEART_RATE, DAILY_STEPS, BPM, STEPS_UNITS, summaries, SUM, AVG, CNT, MIN, MAX, MSR
from ...lib.date import local_date_to_time
from ...squeal import StatisticJournalInteger, StatisticName

# this is really just a daily summary - maybe it should be implemented as such?
# but it would be very inefficient for most stats.  should intervals be improved somehow?

log = getLogger(__name__)
QUARTER_DAY = 6 * 60 * 60


class MonitorCalculator(IntervalCalculatorMixin, MultiProcCalculator):

    def __init__(self, *args, cost_calc=1, cost_write=1, load_once=True, schedule='d', **kargs):
        super().__init__(*args, cost_calc=cost_calc, cost_write=cost_write,
                         load_once=load_once, schedule=schedule, **kargs)

    def _read_data(self, s, interval):
        start, finish = local_date_to_time(interval.start), local_date_to_time(interval.finish)
        midpt = start + 0.5 * (finish - start)
        m0 = s.query(func.avg(func.abs(StatisticJournalInteger.time - midpt))).join(StatisticName). \
            filter(StatisticName.name == HEART_RATE,
                   StatisticName.owner == self.owner_in,
                   StatisticJournalInteger.time < finish,
                   StatisticJournalInteger.time >= start,
                   StatisticJournalInteger.value > 0).scalar()
        log.debug('M0: %s' % m0)
        if m0 and abs(m0 - QUARTER_DAY) < 0.25 * QUARTER_DAY:  # not evenly sampled
            all_hr = [row[0] for row in s.query(StatisticJournalInteger.value).join(StatisticName). \
                filter(StatisticName.name == HEART_RATE,
                       StatisticName.owner == self.owner_in,
                       StatisticJournalInteger.time < finish,
                       StatisticJournalInteger.time >= start,
                       StatisticJournalInteger.value > 0).all()]
            n = len(all_hr)
            rest_heart_rate = sorted(all_hr)[n // 10]  # 10th percentile
        else:
            log.info('Insufficient coverage for %s' % REST_HR)
            rest_heart_rate = None
        daily_steps = s.query(func.sum(StatisticJournalInteger.value)).join(StatisticName). \
            filter(StatisticName.name == STEPS,
                   StatisticName.owner == self.owner_in,
                   StatisticJournalInteger.time < finish,
                   StatisticJournalInteger.time >= start).scalar()
        return rest_heart_rate, daily_steps

    def _calculate_results(self, s, interval, data, loader):
        rest_heart_rate, daily_steps = data
        if rest_heart_rate:
            loader.add(REST_HR, BPM, summaries(AVG, CNT, MIN, MSR), None, interval, rest_heart_rate,
                       local_date_to_time(interval.start), StatisticJournalInteger)
        if daily_steps:
            loader.add(DAILY_STEPS, STEPS_UNITS, summaries(SUM, AVG, CNT, MAX, MSR), None, interval, daily_steps,
                       local_date_to_time(interval.start), StatisticJournalInteger)
