
import datetime as dt
from logging import getLogger

from sqlalchemy.sql import func
from sqlalchemy.sql.functions import count

from . import MultiProcCalculator
from ..names import STEPS, REST_HR, HEART_RATE, DAILY_STEPS, BPM, STEPS_UNITS, summaries, SUM, AVG, CNT, MIN, MAX, MSR
from ..pipeline import LoaderMixin
from ...lib import local_date_to_time, time_to_local_date, to_date, format_date
from ...lib.log import log_current_exception
from ...squeal import MonitorJournal, StatisticJournalInteger, StatisticName, StatisticJournal, Composite, \
    CompositeComponent, Source
from ...squeal.utils import add

log = getLogger(__name__)
QUARTER_DAY = 6 * 60 * 60


class MonitorCalculator(LoaderMixin, MultiProcCalculator):

    '''
    This is a little unusual, in that we can calculate results from partial data and then, when we have
    more data, we need to delete the previous values.  So we need to be careful (1) in deciding when
    we have new data; (2) in avoiding duplicates; and (3) in tracking composite sources.
    '''

    def _missing(self, s):
        # any day that has an unused monitor journal is a missing day
        Composite.clean(s)
        used_sources = s.query(CompositeComponent.input_source_id). \
            join(StatisticJournal, CompositeComponent.output_source_id == StatisticJournal.source_id). \
            join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
            filter(StatisticName.owner == self.owner_out)
        sources = s.query(MonitorJournal).filter(~MonitorJournal.id.in_(used_sources))
        start, finish = self._start_finish(local_date_to_time)
        if start:
            sources = sources.filter(MonitorJournal.finish >= start)
        if finish:
            # don't extend finish - it's 'one past the end'
            sources = sources.filter(MonitorJournal.start <= finish)
        dates = set()
        start, finish = self._start_finish(lambda x: to_date(x, none=True))
        for source in sources.all():
            for date in self._dates_for_source(source):
                if (start is None or start <= date) and (finish is None or date <= finish):
                    dates.add(date)
        missing = sorted(dates)
        if missing:
            log.debug(f'Missing {start} - {finish}: {missing[0]} - {missing[-1]} / {len(missing)}')
        return missing

    @staticmethod
    def _dates_for_source(mjournal):
        start = time_to_local_date(mjournal.start)
        finish = time_to_local_date(mjournal.finish)
        while start <= finish:
            yield start
            start += dt.timedelta(days=1)

    def _delete(self, s):
        start, finish = self._start_finish(local_date_to_time)
        self._delete_time_range(s, start, finish)

    def _delete_time_range(self, s, start, finish):
        composite_ids = s.query(Composite.id). \
            join(StatisticJournal, Composite.id == StatisticJournal.source_id). \
            join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
            filter(StatisticName.owner == self.owner_out)
        if start:
            composite_ids = composite_ids.filter(StatisticJournal.time >= start)
        if finish:
            composite_ids = composite_ids.filter(StatisticJournal.time <= finish)
        log.debug(f'Delete query: {composite_ids}')
        n = s.query(count(Source.id)). \
            filter(Source.id.in_(composite_ids)). \
            scalar()
        if n:
            log.warning(f'Deleting {n} Composite sources ({start} - {finish})')
            s.query(Source). \
                filter(Source.id.in_(composite_ids)). \
                delete(synchronize_session=False)
            s.commit()

    def _run_one(self, s, start):
        # careful here to make summertime work correctly
        finish = local_date_to_time(start + dt.timedelta(days=1))
        start = local_date_to_time(start)
        # delete any previous, incomplete data
        if s.query(count(Composite.id)). \
                join(StatisticJournal, Composite.id == StatisticJournal.source_id). \
                join(StatisticName). \
                filter(StatisticJournal.time >= start,
                       StatisticJournal.time < finish,
                       StatisticName.owner == self.owner_out).scalar():
            self._delete_time_range(s, start, finish)
        try:
            input_source_ids, data = self._read_data(s, start, finish)
            if not input_source_ids:
                raise Exception(f'No sources found on {start}')
            output_source = add(s, Composite(n_components=len(input_source_ids)))
            for input_source_id in input_source_ids:
                s.add(CompositeComponent(input_source_id=input_source_id, output_source=output_source))
            s.commit()
            loader = self._get_loader(s, add_serial=False, clear_timestamp=False)
            self._calculate_results(s, output_source, data, loader, start)
            loader.load()
            self._prev_loader = loader
        except Exception as e:
            log.warning(f'No statistics for {start} - {finish}: ({e})')
            log_current_exception()

    def _read_data(self, s, start, finish):
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
            log.info(f'Insufficient coverage for {REST_HR} for {start} - {finish}')
            rest_heart_rate = None
        daily_steps = s.query(func.sum(StatisticJournalInteger.value)).join(StatisticName). \
            filter(StatisticName.name == STEPS,
                   StatisticName.owner == self.owner_in,
                   StatisticJournalInteger.time < finish,
                   StatisticJournalInteger.time >= start).scalar()
        input_source_ids = [row[0] for row in s.query(MonitorJournal.id).
            filter(MonitorJournal.start < finish,
                   MonitorJournal.finish >= start).all()]
        return input_source_ids, (rest_heart_rate, daily_steps)

    def _calculate_results(self, s, source, data, loader, start):
        rest_heart_rate, daily_steps = data
        if rest_heart_rate:
            loader.add(REST_HR, BPM, summaries(AVG, CNT, MIN, MSR), None, source, rest_heart_rate,
                       start, StatisticJournalInteger)
        loader.add(DAILY_STEPS, STEPS_UNITS, summaries(SUM, AVG, CNT, MAX, MSR), None, source, daily_steps,
                   start, StatisticJournalInteger)

    def _args(self, missing, start, finish):
        start, finish = format_date(missing[start]), format_date(missing[finish])
        log.info(f'Starting worker for {start} - {finish}')
        return f'"{start}" "{finish}"'
