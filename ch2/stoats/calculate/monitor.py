
from sqlalchemy.sql.functions import min, sum

from . import IntervalCalculator
from .summary import SummaryStatistics
from ..names import STEPS, REST_HR, HEART_RATE, DAILY_STEPS, BPM, STEPS_UNITS, summaries, SUM, AVG, CNT, MIN, MAX, MSR
from ..read.monitor import MonitorImporter
from ...lib.date import local_date_to_time
from ...lib.schedule import Schedule
from ...squeal.database import add
from ...squeal.tables.source import Interval, NoStatistics
from ...squeal.tables.statistic import StatisticJournalInteger, StatisticName


# this is really just a daily summary - maybe it should be implemented as such?
# but it would be very inefficient for most stats.  should intervals be improved somehow?


class MonitorStatistics(IntervalCalculator):

    def _run_calculations(self):
        with self._db.session_context() as s:
            try:
                for start, finish in Interval.missing_dates(self._log, s, Schedule('d'), self, MonitorImporter):
                    self._log.info('Processing monitor data from %s to %s' % (start, finish))
                    self._add_stats(s, start, finish)
                    # stealth load so clean out summary manually
                    Interval.clean_dates(s, start, finish, owner=SummaryStatistics)
            except NoStatistics:
                self._log.info('No monitor data to process')

    def _add_stats(self, s, start, finish):
        start_time, finish_time = local_date_to_time(start), local_date_to_time(finish)
        interval = add(s, Interval(schedule='d', owner=self, start=start, finish=finish))
        rest_heart_rate = s.query(min(StatisticJournalInteger.value)).join(StatisticName). \
            filter(StatisticName.name == HEART_RATE,
                   StatisticName.owner == MonitorImporter,
                   StatisticJournalInteger.time < finish_time,
                   StatisticJournalInteger.time >= start_time,
                   StatisticJournalInteger.value > 0).scalar()
        self._add_integer_stat(s, interval, REST_HR, summaries(AVG, CNT, MIN, MSR), rest_heart_rate, BPM, start_time)
        daily_steps = s.query(sum(StatisticJournalInteger.value)).join(StatisticName). \
            filter(StatisticName.name == STEPS,
                   StatisticName.owner == MonitorImporter,
                   StatisticJournalInteger.time < finish_time,
                   StatisticJournalInteger.time >= start_time).scalar()
        self._add_integer_stat(s, interval, DAILY_STEPS, summaries(SUM, AVG, CNT, MAX, MSR),
                               daily_steps, STEPS_UNITS, start_time)
        self._log.debug('Added data for %s' % interval)

    def _add_integer_stat(self, s, journal, name, summary, value, units, time):
        if value is not None:
            StatisticJournalInteger.add(self._log, s, name, units, summary, self, None, journal, value, time)
