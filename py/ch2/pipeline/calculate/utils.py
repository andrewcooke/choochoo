from abc import abstractmethod
from logging import getLogger

from sqlalchemy import not_
from sqlalchemy.sql.functions import count

from ..pipeline import MultiProcPipeline, UniProcPipeline, LoaderMixin
from ...commands.args import STATISTICS
from ...lib import local_time_to_time, time_to_local_time, to_date, format_date, log_current_exception
from ...lib.schedule import Schedule
from ...sql import Timestamp, StatisticName, StatisticJournal, ActivityJournal, ActivityGroup, SegmentJournal, Interval
from ...sql.types import long_cls
from ...sql.utils import add

log = getLogger(__name__)


class CalculatorMixin:

    def __init__(self, *args, start=None, finish=None, **kargs):
        self.start = start  # optional start local time (always present for workers)
        self.finish = finish  # optional finish local time (always present for workers)
        super().__init__(*args, **kargs)

    def _start_finish(self, type=None):
        start, finish = self.start, self.finish
        if type:
            if start: start = type(start)
            if finish: finish = type(finish)
        return start, finish

    def _base_command(self):
        return f'{STATISTICS}'


class MultiProcCalculator(CalculatorMixin, MultiProcPipeline):

    pass


class UniProcCalculator(CalculatorMixin, UniProcPipeline):

    def _base_command(self):
        raise Exception('UniProc does not support workers')

    def _args(self, missing, start, finish):
        raise Exception('UniProc does not support workers')


class JournalCalculatorMixin:
    '''
    auto-detects missing entries, deletes on forcing, and schedules threads via owner_out.

    provides access to the journal via _get_source.
    '''

    _journal_type = None

    def _delimit_query(self, q):
        start, finish = self._start_finish(type=local_time_to_time)
        log.debug(f'Delimit times: {start} - {finish}')
        if start:
            q = q.filter(self._journal_type.start >= start)
        if finish:
            q = q.filter(self._journal_type.start <= finish)
        return q

    def _missing(self, s):
        existing_ids = s.query(Timestamp.source_id).filter(Timestamp.owner == self.owner_out)
        q = s.query(self._journal_type.start). \
            filter(not_(self._journal_type.id.in_(existing_ids.cte()))). \
            order_by(self._journal_type.start)
        return [row[0] for row in self._delimit_query(q)]

    def _args(self, missing, start, finish):
        s, f = time_to_local_time(missing[start]), time_to_local_time(missing[finish])
        log.info(f'Starting worker for {s} - {f}')
        return f'"{s}" "{f}"'

    def _delete(self, s):
        start, finish = self._start_finish(type=local_time_to_time)
        s.commit()   # so that we don't have any risk of having something in the session that can be deleted
        statistic_names = s.query(StatisticName.id).filter(StatisticName.owner == self.owner_out)
        activity_journals = self._delimit_query(s.query(self._journal_type.id))
        statistic_journals = s.query(StatisticJournal.id). \
            filter(StatisticJournal.statistic_name_id.in_(statistic_names.cte()),
                   StatisticJournal.source_id.in_(activity_journals))
        for repeat in range(2):
            if repeat:
                s.query(StatisticJournal).filter(StatisticJournal.id.in_(statistic_journals.cte())). \
                    delete(synchronize_session=False)
                Timestamp.clear_keys(s, activity_journals.cte(), self.owner_out, constraint=None)
            else:
                n = s.query(count(StatisticJournal.id)). \
                    filter(StatisticJournal.id.in_(statistic_journals.cte())).scalar()
                if n:
                    log.warning(f'Deleting {n} statistics for {long_cls(self.owner_out)} from {start} to {finish}')
                else:
                    log.warning(f'No statistics to delete for {long_cls(self.owner_out)} from {start} to {finish}')
        s.commit()

    def _get_source(self, s, time):
        return s.query(self._journal_type).filter(self._journal_type.start == time).one()


class ActivityJournalCalculatorMixin(JournalCalculatorMixin):

    _journal_type = ActivityJournal


class ActivityGroupCalculatorMixin(ActivityJournalCalculatorMixin):

    def __init__(self, *args, activity_group=None, **kargs):
        super().__init__(*args, **kargs)
        self.activity_group = activity_group

    def _missing(self, s):
        existing_ids = s.query(Timestamp.source_id).filter(Timestamp.owner == self.owner_out)
        q = s.query(self._journal_type.start). \
            filter(not_(self._journal_type.id.in_(existing_ids.cte()))). \
            order_by(self._journal_type.start)
        return [row[0] for row in self._delimit_query(q)]

    def _delimit_query(self, q):
        q = super()._delimit_query(q)
        if self.activity_group:
            q = q.join(ActivityGroup).filter(ActivityGroup.name == self.activity_group)
        return q


class SegmentJournalCalculatorMixin(JournalCalculatorMixin):

    _journal_type = SegmentJournal


class DataFrameCalculatorMixin(LoaderMixin):

    def _run_one(self, s, time_or_date):
        source = self._get_source(s, time_or_date)
        with Timestamp(owner=self.owner_out, source=source).on_success(s):
            try:
                # data may be structured (doesn't have to be simply a dataframe)
                data = self._read_dataframe(s, source)
                stats = self._calculate_stats(s, source, data)
                if stats is not None:
                    loader = self._get_loader(s)
                    self._copy_results(s, source, loader, stats)
                    loader.load()
                else:
                    raise Exception('No stats')
            except Exception as e:
                log.error(f'No statistics on {time_or_date}: {e}')
                log_current_exception()

    @abstractmethod
    def _get_source(self, s, time_or_date):
        raise NotImplementedError()

    @abstractmethod
    def _read_dataframe(self, s, source):
        raise NotImplementedError()

    @abstractmethod
    def _calculate_stats(self, s, source, data):
        raise NotImplementedError()

    @abstractmethod
    def _copy_results(self, s, source, loader, stats):
        raise NotImplementedError()


class DirectCalculatorMixin(LoaderMixin):

    def _run_one(self, s, time_or_date):
        source = self._get_source(s, time_or_date)
        with Timestamp(owner=self.owner_out, source=source).on_success(s):
            try:
                data = self._read_data(s, source)
                loader = self._get_loader(s)
                self._calculate_results(s, source, data, loader)
                loader.load()
            except Exception as e:
                log.error(f'No statistics on {time_or_date}: {e}')
                log_current_exception()

    @abstractmethod
    def _get_source(self, s, time_or_date):
        raise NotImplementedError()

    @abstractmethod
    def _read_data(self, s, source):
        raise NotImplementedError()

    @abstractmethod
    def _calculate_results(self, s, source, data, loader):
        raise NotImplementedError()


class IntervalCalculatorMixin(LoaderMixin):

    def __init__(self, *args, schedule='m', grouped=False, **kargs):
        self.schedule = Schedule(self._assert('schedule', schedule))
        self.grouped = grouped
        super().__init__(*args, **kargs)

    def _missing(self, s):
        start, finish = self._start_finish(type=to_date)
        expected = s.query(ActivityGroup).count() + 1 if self.grouped else 1
        return list(Interval.missing_dates(s, expected, self.schedule, self.owner_out, start=start, finish=finish))

    def _args(self, missing, start, finish):
        s, f = format_date(missing[start][0]), format_date(missing[finish][1])
        log.info(f'Starting worker for {s} - {f}')
        return f'"{s}" "{f}"'

    def _delete(self, s):
        start, finish = self._start_finish()
        # we delete the intervals that the statistics depend on and they will cascade
        for repeat in range(2):
            if repeat:
                q = s.query(Interval)
            else:
                q = s.query(count(Interval.id))
            q = q.filter(Interval.schedule == self.schedule,
                         Interval.owner == self.owner_out)
            if start:
                q = q.filter(Interval.finish > start)
            if finish:
                q = q.filter(Interval.start < finish)
            if repeat:
                for interval in q.all():
                    log.debug('Deleting %s' % interval)
                    s.delete(interval)
            else:
                n = q.scalar()
                if n:
                    log.warning('Deleting %d intervals' % n)
                else:
                    log.warning('No intervals to delete')
        s.commit()

    def _run_one(self, s, missing):
        activity_groups = [None] + (list(s.query(ActivityGroup).all()) if self.grouped else [])
        for activity_group in activity_groups:
            log.debug(f'Activity group: {activity_group}')
            if s.query(Interval). \
                    filter(Interval.schedule == self.schedule,
                           Interval.owner == self.owner_out,
                           Interval.start == missing[0],
                           Interval.activity_group == activity_group).one_or_none():
                raise Exception('Interval already exists')
            interval = add(s, Interval(schedule=self.schedule, owner=self.owner_out,
                                       start=missing[0], finish=missing[1], activity_group=activity_group))
            s.commit()
            try:
                data = self._read_data(s, interval)
                loader = self._get_loader(s, add_serial=False, clear_timestamp=False)
                self._calculate_results(s, interval, data, loader)
                loader.load()
            except Exception as e:
                log.error(f'No statistics for {missing} due to error ({e})')
                log_current_exception()

    @abstractmethod
    def _read_data(self, s, interval):
        raise NotImplementedError()

    @abstractmethod
    def _calculate_results(self, s, interval, data, loader):
        raise NotImplementedError()
