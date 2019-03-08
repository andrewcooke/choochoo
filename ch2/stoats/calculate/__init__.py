
from abc import abstractmethod

from sqlalchemy import not_
from sqlalchemy.sql.functions import count

from .. import DbPipeline
from ..waypoint import WaypointReader
from ...lib.date import to_date, local_date_to_time
from ...lib.schedule import Schedule
from ...squeal import ActivityJournal, ActivityGroup, Pipeline, Interval, Timestamp, StatisticJournal, \
    StatisticName
from ...squeal.types import short_cls, long_cls
from ...stoats.load import StatisticJournalLoader


def run_pipeline_after(log, db, type, force_after=None, like=None, **extra_kargs):
    # force_after should be a date, because it's public API not database
    force_after = to_date(force_after, none=True)
    with db.session_context() as s:
        for cls, args, kargs in Pipeline.all(log, s, type, like=like):
            kargs = dict(kargs)
            kargs.update(extra_kargs)
            log.info('Running %s (%s, %s)' % (short_cls(cls), args, kargs))
            cls(log, db, *args, **kargs).run(force_after=force_after)


def run_pipeline_paths(log, db, type, paths, force=False, like=None, **extra_kargs):
    with db.session_context() as s:
        for cls, args, kargs in Pipeline.all(log, s, type, like=like):
            kargs = dict(kargs)
            kargs.update(extra_kargs)
            log.info('Running %s (%s, %s)' % (short_cls(cls), args, kargs))
            cls(log, db, *args, **kargs).run(paths, force=force)


class IntervalCalculator(DbPipeline):
    '''
    Support for calculations associated with intervals.
    '''

    def run(self, force_after=None):
        schedule = Schedule(self._assert_karg('schedule'))
        self.run_schedule(force_after=force_after, schedule=schedule)

    def run_schedule(self, force_after=None, schedule=None):
        if force_after:
            self._delete(after=force_after)
        self._run_calculations(schedule)

    @abstractmethod
    def _run_calculations(self, schedule):
        raise NotImplementedError()

    def _delete(self, after=None):
        self._delete_intervals(after)

    def _delete_intervals(self, after=None):
        # we delete the intervals that all summary statistics depend on and they will cascade
        with self._db.session_context() as s:
            for repeat in range(2):
                if repeat:
                    q = s.query(Interval)
                else:
                    q = s.query(count(Interval.id))
                q = self._filter_intervals(q)
                if after:
                    q = q.filter(Interval.finish > after)
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


class ActivityCalculator(DbPipeline):
    '''
    Support for calculations associated with activity journals (which is most).
    '''

    def __init__(self, log, *args, **kargs):
        self.owner = self  # default for loader, deletion
        super().__init__(log, *args, **kargs)

    def run(self, force_after=None):
        with self._db.session_context() as s:
            for activity_group in s.query(ActivityGroup).all():
                self._log.debug(f'Checking statistics for activity group {activity_group.name}')
                if force_after:
                    self._delete_my_statistics(s, activity_group, after=force_after)
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

    def _delete_my_statistics(self, s, agroup, after=None):
        '''
        Delete all statistics owned by this class and in the activity group.
        Fast because in-SQL.
        '''
        s.commit()   # so that we don't have any risk of having something in the session that can be deleted
        if after:
            after = local_date_to_time(after)
        names = s.query(StatisticName.id).filter(StatisticName.owner == self.owner)
        journals = s.query(StatisticJournal.id). \
            filter(StatisticJournal.statistic_name_id.in_(names.cte()))
        journals = self._constrain_source(s, journals, agroup)
        if after:
            journals = journals.filter(StatisticJournal.time >= after)
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
                    self._log.warning(f'Deleting {n} statistics for {long_cls(self.owner)} / {agroup}')
                else:
                    self._log.warning(f'No statistics to delete for {long_cls(self.owner)} / {agroup}')
                    self._log.debug(journals)
        s.commit()

    def _constrain_source(self, s, q, agroup):
        cte = s.query(ActivityJournal.id).filter(ActivityJournal.activity_group_id == agroup.id).cte()
        return q.filter(StatisticJournal.source_id.in_(cte))


class WaypointCalculator(ActivityCalculator):
    '''
    Original calculator scheme, still used by most code.  Pure-python and SQLAlchemy,
    '''

    def _add_stats(self, s, ajournal):
        owner = self._assert_karg('owner')
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


class DataFrameCalculator(ActivityCalculator):
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
