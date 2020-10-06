from abc import abstractmethod
from logging import getLogger

from sqlalchemy import not_

from ..pipeline import ProcessPipeline
from ...common.date import time_to_local_timeq, format_dateq
from ...common.log import log_current_exception, log_query
from ...lib import local_time_to_time, to_date
from ...lib.schedule import Schedule
from ...sql import Timestamp, ActivityJournal, ActivityGroup, SegmentJournal, Interval
from ...sql.utils import add

log = getLogger(__name__)


class ProcessCalculator(ProcessPipeline): pass


class JournalCalculatorMixin:
    '''
    auto-detects missing entries and schedules threads via owner_out.

    provides access to the journal via _get_source.
    '''

    _journal_type = None

    def _missing(self, s):
        source_ids = self._delimit_timestamp(
            s.query(Timestamp.source_id).filter(Timestamp.owner == self.owner_out))
        q = self._delimit_missing(
            s.query(self._journal_type.start).
                filter(not_(self._journal_type.id.in_(source_ids))).
                order_by(self._journal_type.start))
        return [time_to_local_timeq(row[0]) for row in q]

    def _delimit_missing(self, q):
        return q

    def _delimit_timestamp(self, q):
        return q

    def _get_source(self, s, time):
        return s.query(self._journal_type).filter(self._journal_type.start == time).one()


class ActivityJournalCalculatorMixin(JournalCalculatorMixin):

    _journal_type = ActivityJournal


class ActivityGroupCalculatorMixin(ActivityJournalCalculatorMixin):

    def __init__(self, *args, activity_group=None, **kargs):
        super().__init__(*args, **kargs)
        self.activity_group = activity_group

    def _delimit_missing(self, q):
        return log_query(q.join(ActivityGroup).filter(ActivityGroup.name == self.activity_group),
                         'Missing:')

    def _delimit_timestamp(self, q):
        return q.filter(Timestamp.constraint == self.activity_group)


class SegmentJournalCalculatorMixin(JournalCalculatorMixin):

    _journal_type = SegmentJournal


class DataFrameCalculatorMixin:

    def __init__(self, *args, add_serial=True, timestamp_constraint=None, **kargs):
        self.__add_serial = add_serial
        self.__timestamp_constraint = timestamp_constraint
        super().__init__(*args, **kargs)

    def _run_one(self, missed):
        with self._config.db.session_context() as s:
            log.debug(f'Calculating for {missed}')
            source = self._get_source(s, local_time_to_time(missed))
            with Timestamp(owner=self.owner_out, source=source, constraint=self.__timestamp_constraint).on_success(s):
                try:
                    # data may be structured (doesn't have to be simply a dataframe)
                    data = self._read_dataframe(s, source)
                    stats = self._calculate_stats(s, source, data)
                    if stats is not None:
                        loader = self._get_loader(s, add_serial=self.__add_serial)
                        self._copy_results(s, source, loader, stats)
                        loader.load()
                    else:
                        raise Exception('No stats')
                except Exception as e:
                    log.error(f'No statistics on {missed}: {e}')
                    log_current_exception(traceback=True)

    @abstractmethod
    def _get_source(self, s, time):
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


class IntervalCalculatorMixin:

    def __init__(self, *args, schedule='m', grouped=False, permanent=False, **kargs):
        self.schedule = Schedule(self._assert('schedule', schedule))
        self.grouped = grouped
        self.permanent = permanent
        super().__init__(*args, **kargs)

    def _missing(self, s):
        from .summary import SummaryCalculator
        expected = s.query(ActivityGroup).count() + 1 if self.grouped else 1

        return [format_dateq(start)
                for start in Interval.missing_starts(s, expected, self.schedule, self.owner_out,
                                                     exclude_owners=(SummaryCalculator,))]

    def _run_one(self, missed):
        start = to_date(missed)
        with self._config.db.session_context() as s:
            activity_groups = [None] + (list(s.query(ActivityGroup).all()) if self.grouped else [])
            for activity_group in activity_groups:
                log.debug(f'Activity group: {activity_group}; Schedule: {self.schedule}')
                if s.query(Interval). \
                        filter(Interval.schedule == self.schedule,
                               Interval.owner == self.owner_out,
                               Interval.start == start,
                               Interval.activity_group == activity_group).one_or_none():
                    # we can have some activity groups, but not others
                    log.warning(f'Interval already exists for '
                                f'{activity_group} / {self.schedule} at {missed}')
                else:
                    interval = add(s, Interval(schedule=self.schedule, owner=self.owner_out,
                                               start=start, activity_group=activity_group,
                                               permanent=self.permanent))
                    s.commit()
                    try:
                        data = self._read_data(s, interval)
                        loader = self._get_loader(s, add_serial=False, clear_timestamp=False)
                        self._calculate_results(s, interval, data, loader)
                        loader.load()
                    except Exception as e:
                        log.error(f'No statistics for {missed} due to error ({e})')
                        log_current_exception()

    @abstractmethod
    def _read_data(self, s, interval):
        raise NotImplementedError()

    @abstractmethod
    def _calculate_results(self, s, interval, data, loader):
        raise NotImplementedError()
