
import datetime as dt
from logging import getLogger

from sqlalchemy.sql import func

from . import MultiProcCalculator, CompositeCalculatorMixin
from ..names import STEPS, REST_HR, HEART_RATE, DAILY_STEPS, BPM, STEPS_UNITS, summaries, SUM, AVG, CNT, MIN, MAX, MSR
from ...lib import local_date_to_time
from ...squeal import MonitorJournal, StatisticJournalInteger, StatisticName

log = getLogger(__name__)
QUARTER_DAY = 6 * 60 * 60


class MonitorCalculator(CompositeCalculatorMixin, MultiProcCalculator):

    def _missing(self, s):
        missing = super()._missing(s)
        if missing:
            # we may need to back up one day since the last data could be incomplete
            start = missing[0]
            if s.query(MonitorJournal).filter(MonitorJournal.start < local_date_to_time(start)).limit(1).one_or_none():
                log.debug('Back-up one day')
                start = start - dt.timedelta(days=1)
                missing = [start] + missing
        return missing

    def _unused_sources_given_used(self, s, used_sources):
        return self._unused_sources_given_used_and_class(s, used_sources, MonitorJournal)

    def _read_data(self, s, start, finish):
        midpt = start + dt.timedelta(hours=12)
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
            log.info(f'Insufficient coverage for {REST_HR} for {start} - {finish}')
            rest_heart_rate = None
        daily_steps = s.query(func.sum(StatisticJournalInteger.value)).join(StatisticName). \
            filter(StatisticName.name == STEPS,
                   StatisticName.owner == self.owner_in,
                   StatisticJournalInteger.time < finish,
                   StatisticJournalInteger.time >= start).scalar()
        input_source_ids = [row[0] for row in s.query(MonitorJournal.id).
            filter(MonitorJournal.start <= finish,
                   MonitorJournal.finish >= start).all()]
        return input_source_ids, (rest_heart_rate, daily_steps)

    def _calculate_results(self, s, source, data, loader, start, finish):
        rest_heart_rate, daily_steps = data
        if rest_heart_rate:
            loader.add(REST_HR, BPM, summaries(AVG, CNT, MIN, MSR), None, source, rest_heart_rate,
                       start, StatisticJournalInteger)
        loader.add(DAILY_STEPS, STEPS_UNITS, summaries(SUM, AVG, CNT, MAX, MSR), None, source, daily_steps,
                   start, StatisticJournalInteger)
