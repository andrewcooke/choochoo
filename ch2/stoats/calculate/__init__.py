
from abc import abstractmethod
from logging import getLogger

from sqlalchemy import not_
from sqlalchemy.sql.functions import count

from ch2.stoats.pipeline import LoaderMixin
from ..pipeline import MultiProcPipeline, UniProcPipeline
from ..waypoint import WaypointReader
from ...commands.args import STATISTICS, WORKER, mm
from ...lib.date import local_time_to_time, time_to_local_time, format_date, to_date
from ...lib.log import log_current_exception
from ...lib.schedule import Schedule
from ...squeal import ActivityJournal, Interval, Timestamp, StatisticJournal, StatisticName
from ...squeal.types import long_cls
from ...squeal.utils import add

log = getLogger(__name__)


class CalculatorMixin:

    def __init__(self, *args, owner_in=None, start=None, finish=None, **kargs):
        self.owner_in = self._assert('owner_in', owner_in)
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
        return f'{{ch2}} -v0 -l {{log}} {STATISTICS} {mm(WORKER)} {self.id}'


class MultiProcCalculator(CalculatorMixin, MultiProcPipeline):

    pass


class UniProcCalculator(CalculatorMixin, UniProcPipeline):

    def _base_command(self):
        raise Exception('UniProc does not support workers')

    def _args(self, missing, start, finish):
        raise Exception('UniProc does not support workers')


class ActivityJournalCalculatorMixin:

    def _delimit_query(self, q):
        start, finish = self._start_finish(type=local_time_to_time)
        log.debug(f'Delimit times: {start} - {finish}')
        if start:
            q = q.filter(ActivityJournal.start >= start)
        if finish:
            q = q.filter(ActivityJournal.start <= finish)
        return q

    def _missing(self, s):
        existing_ids = s.query(Timestamp.key).filter(Timestamp.owner == self.owner_out)
        q = s.query(ActivityJournal.start). \
            filter(not_(ActivityJournal.id.in_(existing_ids.cte()))). \
            order_by(ActivityJournal.start)
        return [row[0] for row in self._delimit_query(q)]

    def _args(self, missing, start, finish):
        s, f = time_to_local_time(missing[start]), time_to_local_time(missing[finish])
        log.info(f'Starting worker for {s} - {f}')
        return f'"{s}" "{f}"'

    def _delete(self, s):
        start, finish = self._start_finish(type=local_time_to_time)
        s.commit()   # so that we don't have any risk of having something in the session that can be deleted
        statistic_names = s.query(StatisticName.id).filter(StatisticName.owner == self.owner_out)
        activity_journals = self._delimit_query(s.query(ActivityJournal.id))
        statistic_journals = s.query(StatisticJournal.id). \
            filter(StatisticJournal.statistic_name_id.in_(statistic_names.cte()),
                   StatisticJournal.source_id.in_(activity_journals))
        for repeat in range(2):
            if repeat:
                s.query(StatisticJournal).filter(StatisticJournal.id.in_(statistic_journals.cte())). \
                    delete(synchronize_session=False)
                Timestamp.clean_keys(log, s, activity_journals.cte(), self.owner_out, constraint=None)
            else:
                n = s.query(count(StatisticJournal.id)). \
                    filter(StatisticJournal.id.in_(statistic_journals.cte())).scalar()
                if n:
                    log.warning(f'Deleting {n} statistics for {long_cls(self.owner_out)} from {start} to {finish}')
                else:
                    log.warning(f'No statistics to delete for {long_cls(self.owner_out)} from {start} to {finish}')
                    # log.debug(statistic_journals)
        s.commit()

    def _get_source(self, s, time):
        return s.query(ActivityJournal).filter(ActivityJournal.start == time).one()


class DataFrameCalculatorMixin(LoaderMixin):

    def _run_one(self, s, time_or_date):
        source = self._get_source(s, time_or_date)
        with Timestamp(owner=self.owner_out, key=source.id).on_success(log, s):
            try:
                # data may be structured (doesn't have to be simply a dataframe)
                data = self._read_dataframe(s, source)
                stats = self._calculate_stats(s, source, data)
                loader = self._get_loader(s)
                self._copy_results(s, source, loader, stats)
                loader.load()
            except Exception as e:
                log.warning(f'No statistics on {time_or_date}')
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
        with Timestamp(owner=self.owner_out, key=source.id).on_success(log, s):
            try:
                data = self._read_data(s, source)
                loader = self._get_loader(s)
                self._calculate_results(s, source, data, loader)
                loader.load()
            except Exception as e:
                log.warning(f'No statistics on {time_or_date}')
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


class WaypointCalculatorMixin(DirectCalculatorMixin):

    # todo - can / should this be replaced by a data-frame approach?

    def _read_data(self, s, source):
        waypoints = list(WaypointReader().read(s, source, self._names(), self._assert('owner_in', self.owner_in)))
        if not waypoints:
            raise Exception('No waypoints')
        else:
            return waypoints

    @abstractmethod
    def _names(self):
        raise NotImplementedError()


class IntervalCalculatorMixin(LoaderMixin):

    def __init__(self, *args, schedule='m', load_once=False, **kargs):
        self.schedule = Schedule(self._assert('schedule', schedule))
        self.load_once = load_once
        self._prev_loader = None
        super().__init__(*args, **kargs)

    def _missing(self, s):
        start, finish = self._start_finish(type=to_date)
        return list(Interval.missing_dates(log, s, self.schedule, self.owner_out, start=start, finish=finish))

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
            q = q.filter(Interval.owner == self.owner_out)
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
        if s.query(Interval). \
            filter(Interval.schedule == self.schedule,
                   Interval.owner == self.owner_out,
                   Interval.start == missing[0]).one_or_none():
            raise Exception('Interval already exists')
        interval = add(s, Interval(schedule=self.schedule, owner=self.owner_out,
                                   start=missing[0], finish=missing[1]))
        s.commit()
        try:
            data = self._read_data(s, interval)
            if self.load_once and self._prev_loader:
                loader = self._prev_loader
            else:
                loader = self._get_loader(s, add_serial=False, clear_timestamp=False)
            self._calculate_results(s, interval, data, loader)
            if not self.load_once:
                loader.load()
            self._prev_loader = loader
        except Exception as e:
            log.warning(f'No statistics for {missing} due to error ({e})')
            log_current_exception()
            if not self.load_once:
                self._prev_loader = None

    def _shutdown(self, s):
        if self.load_once and self._prev_loader:
            log.debug('Single load')
            self._prev_loader.load()

    @abstractmethod
    def _read_data(self, s, interval):
        raise NotImplementedError()

    @abstractmethod
    def _calculate_results(self, s, interval, data, loader):
        raise NotImplementedError()
