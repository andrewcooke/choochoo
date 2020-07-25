from abc import abstractmethod
from logging import getLogger

from sqlalchemy import not_
from sqlalchemy.sql.functions import count

from ..pipeline import ProcessPipeline
from ...common.date import time_to_local_timeq, format_dateq
from ...common.log import log_current_exception
from ...lib import local_time_to_time, to_date
from ...lib.schedule import Schedule
from ...sql import Timestamp, StatisticName, StatisticJournal, ActivityJournal, ActivityGroup, SegmentJournal, Interval
from ...sql.types import short_cls
from ...sql.utils import add

log = getLogger(__name__)


class ProcessCalculator(ProcessPipeline): pass


class JournalCalculatorMixin:
    '''
    auto-detects missing entries, deletes on forcing, and schedules threads via owner_out.

    provides access to the journal via _get_source.
    '''

    _journal_type = None

    def _missing(self, s):
        existing_ids = s.query(Timestamp.source_id).filter(Timestamp.owner == self.owner_out)
        q = s.query(self._journal_type.start). \
            filter(not_(self._journal_type.id.in_(existing_ids))). \
            order_by(self._journal_type.start)
        return [time_to_local_timeq(row[0]) for row in self._delimit_missing(q)]

    def _delimit_missing(self, q):
        return q

    def _delete(self, s):
        # delete statistics created by this calculator
        statistic_names = s.query(StatisticName.id).filter(StatisticName.owner == self.owner_out)
        statistic_journals = self._delimit_delete(s.query(StatisticJournal).
                                                  filter(StatisticJournal.statistic_name_id.in_(statistic_names)))
        for repeat in range(2):
            if repeat:
                statistic_journals.delete(synchronize_session=False)
                Timestamp.clear(s, self.owner_out, constraint=None)
            else:
                n = statistic_journals.count()
                if n:
                    log.warning(f'Deleting {n} statistics for {short_cls(self.owner_out)}')
                else:
                    log.warning(f'No statistics to delete for {short_cls(self.owner_out)}')

    def _delimit_delete(self, q):
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
        return q.join(ActivityGroup).filter(ActivityGroup.name == self.activity_group)

    def _delimit_delete(self, q):
        return q.join(ActivityJournal).join(ActivityGroup).filter(ActivityGroup.name == self.activity_group)


class SegmentJournalCalculatorMixin(JournalCalculatorMixin):

    _journal_type = SegmentJournal


class DataFrameCalculatorMixin:

    def __init__(self, *args, add_serial=True, **kargs):
        self.__add_serial = add_serial
        super().__init__(*args, **kargs)

    def _run_one(self, missed):
        with self._config.db.session_context() as s:
            log.debug(f'Calculating for {missed}')
            source = self._get_source(s, local_time_to_time(missed))
            with Timestamp(owner=self.owner_out, source=source).on_success(s):
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

    def __init__(self, *args, schedule='m', grouped=False, **kargs):
        self.schedule = Schedule(self._assert('schedule', schedule))
        self.grouped = grouped
        super().__init__(*args, **kargs)

    def _missing(self, s):
        from .summary import SummaryCalculator
        expected = s.query(ActivityGroup).count() + 1 if self.grouped else 1
        return [format_dateq(start)
                for start in Interval.missing_starts(s, expected, self.schedule, self.owner_out,
                                                     exclude_owners=(SummaryCalculator,))]

    def _delete(self, s):
        # we delete the intervals that the statistics depend on and they will cascade
        for repeat in range(2):
            if repeat:
                q = s.query(Interval)
            else:
                q = s.query(count(Interval.id))
            q = q.filter(Interval.schedule == self.schedule, Interval.owner == self.owner_out)
            if repeat:
                for interval in q.all():
                    log.debug(f'Deleting {interval}')
                    s.delete(interval)
            else:
                n = q.scalar()
                if n:
                    log.warning(f'Deleting {n} intervals')
                else:
                    log.warning('No intervals to delete')

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
                                               start=start, activity_group=activity_group))
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
