
from sqlalchemy.sql import func

from . import IntervalStatistics
from .summary import SummaryStatistics
from ..names import STEPS, REST_HR, HEART_RATE, DAILY_STEPS, BPM, STEPS_UNITS, summaries, SUM, AVG, CNT, MIN, MAX, MSR
from ..read.monitor import MonitorReader
from ...lib.date import local_date_to_time
from ...squeal import Interval, StatisticJournalInteger, StatisticName, NoStatistics
from ...squeal.utils import add

# this is really just a daily summary - maybe it should be implemented as such?
# but it would be very inefficient for most stats.  should intervals be improved somehow?


QUARTER_DAY = 6 * 60 * 60


class MonitorStatistics(IntervalStatistics):

    def _on_init(self, *args, **kargs):
        kargs['schedule'] = 'd'
        super()._on_init(*args, **kargs)

    def _run_calculations(self, schedule):
        with self._db.session_context() as s:
            try:
                for start, finish in Interval.missing_dates(self._log, s, schedule, self, MonitorReader):
                    self._log.info('Processing monitor data from %s to %s' % (start, finish))
                    self._add_stats(s, start, finish)
                    # stealth load so clean out summary manually
                    Interval.clean_dates(self._log, s, start, finish, owner=SummaryStatistics)
            except NoStatistics:
                self._log.info('No monitor data to process')

    def _add_stats(self, s, start, finish):
        start_time, finish_time = local_date_to_time(start), local_date_to_time(finish)
        interval = add(s, Interval(schedule='d', owner=self, start=start, finish=finish))
        midpt = start_time + 0.5 * (finish_time - start_time)
        m0 = s.query(func.avg(func.abs(StatisticJournalInteger.time - midpt))).join(StatisticName). \
            filter(StatisticName.name == HEART_RATE,
                   StatisticName.owner == MonitorReader,  # todo - owner?
                   StatisticJournalInteger.time < finish_time,
                   StatisticJournalInteger.time >= start_time,
                   StatisticJournalInteger.value > 0).scalar()
        self._log.debug('M0: %s' % m0)
        if m0 and abs(m0 - QUARTER_DAY) < 0.25 * QUARTER_DAY:  # not evenly sampled
            all_hr = [row[0] for row in s.query(StatisticJournalInteger.value).join(StatisticName). \
                filter(StatisticName.name == HEART_RATE,
                       StatisticName.owner == MonitorReader,  # todo - owner
                       StatisticJournalInteger.time < finish_time,
                       StatisticJournalInteger.time >= start_time,
                       StatisticJournalInteger.value > 0).all()]
            n = len(all_hr)
            rest_heart_rate = sorted(all_hr)[n // 10]  # 10th percentile
            self._add_integer_stat(s, interval, REST_HR, summaries(AVG, CNT, MIN, MSR), rest_heart_rate, BPM,
                                   start_time)
        else:
            self._log.info('Insufficient coverage for %s' % REST_HR)
        daily_steps = s.query(func.sum(StatisticJournalInteger.value)).join(StatisticName). \
            filter(StatisticName.name == STEPS,
                   StatisticName.owner == MonitorReader,  # todo - owner?
                   StatisticJournalInteger.time < finish_time,
                   StatisticJournalInteger.time >= start_time).scalar()
        self._add_integer_stat(s, interval, DAILY_STEPS, summaries(SUM, AVG, CNT, MAX, MSR),
                               daily_steps, STEPS_UNITS, start_time)
        self._log.debug('Added data for %s' % interval)

    def _add_integer_stat(self, s, journal, name, summary, value, units, time):
        if value is not None:
            StatisticJournalInteger.add(self._log, s, name, units, summary, self, None, journal, value, time)
