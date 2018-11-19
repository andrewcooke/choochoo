
from sqlalchemy.sql.functions import min, sum

from . import Calculator
from ..names import STEPS, REST_HR, HEART_RATE, DAILY_STEPS, BPM, STEPS_UNITS
from ...lib.date import local_date_to_time
from ...lib.schedule import Schedule
from ...squeal.database import add
from ...squeal.tables.source import Interval, NoStatistics
from ...squeal.tables.statistic import StatisticJournalInteger, StatisticName
from ...stoats.calculate.summary import SummaryStatistics
from ...stoats.read.monitor import MonitorImporter


# this is really just a daily summary - maybe it should be implemented as such?
# but it would be very inefficient for most stats.  should intervals be improved somehow?


class MonitorStatistics(Calculator):

    def run(self, force=False, after=None):
        if force:
            self._delete(after=after)
        self._run_monitor()

    def _delete(self, after=None):
        self._delete_intervals(after)

    def _filter_intervals(self, q):
        return q.filter(Interval.owner == self)

    def _run_monitor(self):
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
        self._add_integer_stat(s, interval, REST_HR, '[min],[avg],[cnt]', rest_heart_rate, BPM, start_time)
        daily_steps = s.query(sum(StatisticJournalInteger.value)).join(StatisticName). \
            filter(StatisticName.name == STEPS,
                   StatisticName.owner == MonitorImporter,
                   StatisticJournalInteger.time < finish_time,
                   StatisticJournalInteger.time >= start_time).scalar()
        self._add_integer_stat(s, interval, DAILY_STEPS, '[sum],[avg],[cnt],[min],[max]', daily_steps, STEPS_UNITS,
                               start_time)
        self._log.debug('Added data for %s' % interval)

    def _add_integer_stat(self, s, journal, name, summary, value, units, time):
        if value is not None:
            StatisticJournalInteger.add(self._log, s, name, units, summary, self, None, journal, value, time)
