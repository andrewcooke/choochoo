
import datetime as dt

from sqlalchemy.sql.functions import count, min, sum

from ..names import STEPS, REST_HR
from ...lib.schedule import TZSchedule
from ...squeal.database import add
from ...squeal.tables.monitor import MonitorJournal, MonitorSteps, MonitorHeartRate
from ...squeal.tables.source import Interval
from ...squeal.tables.statistic import StatisticJournalInteger


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
            for start, finish in Interval.missing(self._log, s, TZSchedule('d'), self):
                self._log.info('Processing monitor data from %s to %s' % (start, finish))
                self._add_stats(s, start, finish)

    def _add_stats(self, s, start, finish):
        interval = add(s, Interval(schedule='d', owner=self, time=start, finish=finish))
        self._log.info('Adding monitor data for %s' % start)
        rest_heart_rate = s.query(min(MonitorHeartRate.value)).join(MonitorJournal). \
            filter(MonitorJournal.time < finish,
                   MonitorJournal.finish >= start,
                   MonitorHeartRate.time >= start,
                   MonitorHeartRate.time < finish,
                   MonitorHeartRate.value > 0).scalar()
        self._add_integer_stat(s, interval, REST_HR, '[min],[avg]', rest_heart_rate, 'bpm')
        steps = s.query(sum(MonitorSteps.delta)).join(MonitorJournal). \
            filter(MonitorJournal.time < finish,
                   MonitorJournal.finish >= start,
                   MonitorSteps.time >= start,
                   MonitorSteps.time < finish).scalar()
        self._add_integer_stat(s, interval, STEPS, '[sum],[avg]', steps, None)

    def _add_integer_stat(self, s, journal, name, summary, value, units):
        if value is not None:
            StatisticJournalInteger.add(self._log, s, name, units, summary, self, None, journal, value)
