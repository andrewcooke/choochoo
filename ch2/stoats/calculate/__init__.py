
from abc import abstractmethod
from logging import getLogger
from sys import exc_info
from traceback import format_tb

from sqlalchemy import not_
from sqlalchemy.sql.functions import count

from ..load import StatisticJournalLoader
from ..pipeline import MultiProcPipeline, DbPipeline
from ..waypoint import WaypointReader
from ...commands.args import STATISTICS, WORKER, mm
from ...lib.date import local_date_to_time, local_time_to_time
from ...lib.schedule import Schedule
from ...squeal import ActivityJournal, ActivityGroup, Interval, Timestamp, StatisticJournal, StatisticName
from ...squeal.types import short_cls, long_cls

log = getLogger(__name__)


class Statistics(DbPipeline): pass


class IntervalStatistics(Statistics):
    '''
    Support for calculations associated with intervals.
    '''

    def run(self):
        schedule = Schedule(self._karg('schedule'))
        if self._force():
            self._delete()
        self._run_calculations(schedule)

    @abstractmethod
    def _run_calculations(self, schedule):
        raise NotImplementedError()

    def _delete(self):
        start, finish = self._start_finish()
        # we delete the intervals that all summary statistics depend on and they will cascade
        with self._db.session_context() as s:
            for repeat in range(2):
                if repeat:
                    q = s.query(Interval)
                else:
                    q = s.query(count(Interval.id))
                q = self._filter_intervals(q)
                if start:
                    q = q.filter(Interval.finish >= start)
                if finish:
                    q = q.filter(Interval.start < finish)
                if repeat:
                    for interval in q.all():
                        self._log.debug('Deleting %s' % interval)
                        s.delete(interval)
                else:
                    n = q.scalar()
                    if n:
                        self._log.warning('Deleting %d intervals' % n)
                    else:
                        self._log.warning('No intervals to delete')

    def _filter_intervals(self, q):
        return q.filter(Interval.owner == self)


class ActivityStatistics(Statistics):
    '''
    Support for calculations associated with activity journals (which is most).
    '''

    def __init__(self, log, *args, **kargs):
        self.owner = self  # default for loader, deletion
        super().__init__(log, *args, **kargs)

    def run(self):
        with self._db.session_context() as s:
            for activity_group in s.query(ActivityGroup).all():
                self._log.debug(f'Checking statistics for activity group {activity_group.name}')
                if self._force():
                    self._delete_my_statistics(s, activity_group)
                self._run_activity(s, activity_group)

    def _run_activity(self, s, activity_group):
        for ajournal in self._activity_journals_with_missing_data(s, activity_group):
            # set constraint so we can delete on force
            with Timestamp(owner=self.owner, constraint=activity_group, key=ajournal.id).on_success(self._log, s):
                self._log.info('Running %s for %s' % (short_cls(self), ajournal))
                self._add_stats(s, ajournal)

    def _activity_journals_with_missing_data(self, s, activity_group):
        existing_ids = s.query(Timestamp.key). \
            filter(Timestamp.owner == self.owner,
                   Timestamp.constraint == activity_group).cte()
        yield from s.query(ActivityJournal). \
            filter(not_(ActivityJournal.id.in_(existing_ids)),
                   ActivityJournal.activity_group == activity_group). \
            order_by(ActivityJournal.start).all()

    @abstractmethod
    def _filter_statistic_journals(self, q):
        raise NotImplementedError()

    @abstractmethod
    def _add_stats(self, s, ajournal):
        raise NotImplementedError()

    def _delete_my_statistics(self, s, agroup):
        '''
        Delete all statistics owned by this class and in the activity group.
        Fast because in-SQL.
        '''
        start, finish = self._start_finish(local_date_to_time)
        s.commit()   # so that we don't have any risk of having something in the session that can be deleted
        names = s.query(StatisticName.id).filter(StatisticName.owner == self.owner)
        journals = s.query(StatisticJournal.id). \
            filter(StatisticJournal.statistic_name_id.in_(names.cte()))
        journals = self._constrain_source(s, journals, agroup)
        if start:
            journals = journals.filter(StatisticJournal.time >= start)
        if finish:
            journals = journals.filter(StatisticJournal.time < finish)
        for repeat in range(2):
            if repeat:
                s.query(StatisticJournal).filter(StatisticJournal.id.in_(journals.cte())). \
                    delete(synchronize_session=False)
                Timestamp.clean_keys(self._log, s,
                                     s.query(StatisticJournal.source_id).
                                     filter(StatisticJournal.statistic_name_id.in_(names.cte())),
                                     self.owner, constraint=agroup)
            else:
                n = s.query(count(StatisticJournal.id)).filter(StatisticJournal.id.in_(journals.cte())).scalar()
                if n:
                    self._log.warning(f'Deleting {n} statistics for {long_cls(self.owner)} / {agroup} '
                                      f'from {start} to {finish}')
                else:
                    self._log.warning(f'No statistics to delete for {long_cls(self.owner)} / {agroup} '
                                      f'from {start} to {finish}')
                    self._log.debug(journals)
        s.commit()

    def _constrain_source(self, s, q, agroup):
        cte = s.query(ActivityJournal.id).filter(ActivityJournal.activity_group_id == agroup.id).cte()
        return q.filter(StatisticJournal.source_id.in_(cte))


class WaypointStatistics(ActivityStatistics):
    '''
    Original calculator scheme, still used by most code.  Pure-python and SQLAlchemy,
    '''

    def _add_stats(self, s, ajournal):
        owner = self._karg('owner')
        waypoints = list(WaypointReader(self._log).read(s, ajournal, self._names(), owner))
        if waypoints:
            self._add_stats_from_waypoints(s, ajournal, waypoints)
        else:
            self._log.warning('No statistics for %s' % ajournal)

    @abstractmethod
    def _add_stats_from_waypoints(self, s, ajournal, waypoints):
        raise NotImplementedError()

    @abstractmethod
    def _names(self):
        raise NotImplementedError()


class DataFrameStatistics(ActivityStatistics):
    '''
    New calculator scheme.  Uses data frames / shares code with analysis.
    '''

    def _add_stats(self, s, ajournal):
        df = self._load_data(s, ajournal)
        if df is not None and len(df):
            stats = self._calculate_stats(s, ajournal, df)
            loader = StatisticJournalLoader(self._log, s, self.owner)
            self._copy_results(s, ajournal, loader, stats)
            loader.load()
        else:
            self._log.warning('No statistics for %s' % ajournal)

    @abstractmethod
    def _load_data(self, s, ajournal):
        raise NotImplementedError()

    @abstractmethod
    def _calculate_stats(self, s, ajournal, df):
        raise NotImplementedError()

    @abstractmethod
    def _copy_results(self, s, ajournal, loader, stats):
        raise NotImplementedError()


class MultiProcCalculator(MultiProcPipeline):

    def _base_command(self):
        return f'{{ch2}} -v0 -l {{log}} {STATISTICS} {mm(WORKER)} {self.id}'


class DataFrameCalculator(MultiProcCalculator):

    def _run_one(self, s, time_or_date):
        source = self._get_source(s, time_or_date)
        with Timestamp(owner=self.owner_out, key=source.id).on_success(log, s):
            try:
                data = self._load_data(s, source)
                stats = self._calculate_stats(s, source, data)
                loader = StatisticJournalLoader(log, s, self.owner_out)
                self._copy_results(s, source, loader, stats)
                loader.load()
            except Exception as e:
                log.warning(f'No statistics on {time_or_date} ({e})')
                log.debug('\n' + ''.join(format_tb(exc_info()[2])))

    @abstractmethod
    def _get_source(self, s, time_or_date):
        raise NotImplementedError()

    @abstractmethod
    def _load_data(self, s, source):
        raise NotImplementedError()

    @abstractmethod
    def _calculate_stats(self, s, source, data):
        raise NotImplementedError()

    @abstractmethod
    def _copy_results(self, s, source, loader, stats):
        raise NotImplementedError()


class ActivityJournalCalculator(DataFrameCalculator):

    def __delimit_query(self, q):
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
        return [row[0] for row in self.__delimit_query(q)]

    def _delete(self, s):
        start, finish = self._start_finish(type=local_time_to_time)
        s.commit()   # so that we don't have any risk of having something in the session that can be deleted
        statistic_names = s.query(StatisticName.id).filter(StatisticName.owner == self.owner_out)
        activity_journals = self.__delimit_query(s.query(ActivityJournal.id))
        statistic_journals = s.query(StatisticJournal.id). \
            filter(StatisticJournal.statistic_name_id.in_(statistic_names.cte()),
                   StatisticJournal.source_id.in_(activity_journals))
        for repeat in range(2):
            if repeat:
                s.query(StatisticJournal).filter(StatisticJournal.id.in_(statistic_journals.cte())). \
                    delete(synchronize_session=False)
                Timestamp.clean_keys(log, s,
                                     s.query(StatisticJournal.source_id).
                                     filter(StatisticJournal.statistic_name_id.in_(statistic_names.cte())),
                                     self.owner_out, constraint=None)
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
