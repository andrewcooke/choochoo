from ch2.stoats.read.monitor import MonitorImporter
from sqlalchemy.sql.functions import count, min, sum

from ..names import STEPS, REST_HR, HEART_RATE, DAILY_STEPS, BPM
from ...lib.date import local_date_to_time
from ...lib.schedule import Schedule
from ...squeal.database import add
from ...squeal.tables.monitor import MonitorJournal
from ...squeal.tables.source import Interval
from ...squeal.tables.statistic import StatisticJournalInteger, StatisticName


# this is really just a daily interval - maybe it should be implemented as such?
# but it would be very inefficient for most stats.  should intervals be improved somehow?


class MonitorStatistics:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    def run(self, force=False, after=None):
        if force:
            self._delete(after=after)
        self._run()

    def _delete(self, after=None):
        # we delete the intervals that all summary statistics depend on and they will cascade
        with self._db.session_context() as s:
            for repeat in range(2):
                if repeat:
                    q = s.query(Interval)
                else:
                    q = s.query(count(Interval.id))
                q = q.filter(Interval.owner == self)
                if after:
                    q = q.filter(Interval.finish > after)
                if repeat:
                    for interval in q.all():
                        self._log.debug('Deleting %s' % interval)
                        s.delete(interval)
                else:
                    n = q.scalar()
                    if n:
                        self._log.warn('Deleting %d intervals' % n)
                    else:
                        self._log.warn('No intervals to delete')

    def _run(self):
        with self._db.session_context() as s:
            for start, finish in Interval.missing(self._log, s, Schedule('d'), self):
                self._log.info('Processing monitor data from %s to %s' % (start, finish))
                self._add_stats(s, start, finish)

    def _add_stats(self, s, start, finish):
        start_time, finish_time = local_date_to_time(start), local_date_to_time(finish)
        interval = add(s, Interval(schedule='d', owner=self,
                                   start=start, finish=finish))
        heart_rate_name = s.query(StatisticName). \
            filter(StatisticName.name == HEART_RATE,
                   StatisticName.owner == MonitorImporter).one_or_none()
        if heart_rate_name:
            rest_heart_rate = s.query(min(StatisticJournalInteger.value)). \
                filter(StatisticJournalInteger.statistic_name == heart_rate_name,
                       StatisticJournalInteger.time < finish_time,
                       StatisticJournalInteger.time >= start_time,
                       StatisticJournalInteger.value > 0).scalar()
            self._add_integer_stat(s, interval, REST_HR, '[min],[avg],[cnt]', rest_heart_rate, BPM)
        steps_name = s.query(StatisticName). \
            filter(StatisticName.name == STEPS,
                   StatisticName.owner == MonitorImporter).one_or_none()
        if steps_name:
            daily_steps = s.query(sum(StatisticJournalInteger.value)). \
                filter(StatisticJournalInteger.statistic_name == steps_name,
                       StatisticJournalInteger.time < finish_time,
                       StatisticJournalInteger.time >= start_time).scalar()
            self._add_integer_stat(s, interval, DAILY_STEPS, '[sum],[avg],[cnt]', daily_steps, STEPS)
        self._log.debug('Added data for %s' % interval)

    def _add_integer_stat(self, s, journal, name, summary, value, units):
        if value is not None:
            StatisticJournalInteger.add(self._log, s, name, units, summary, self, None, journal, value)
