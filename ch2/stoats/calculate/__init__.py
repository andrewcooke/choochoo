
from abc import abstractmethod

from sqlalchemy.sql.functions import count

from .waypoint import WaypointReader
from ...lib.date import to_time
from ...squeal.tables.activity import ActivityJournal, ActivityGroup
from ...squeal.tables.pipeline import Pipeline
from ...squeal.tables.source import Interval
from ...squeal.tables.statistic import StatisticJournal, StatisticName, StatisticJournalFloat
from ...squeal.types import short_cls


def run_pipeline_after(log, db, type, after=None, force=False, like=None):
    with db.session_context() as s:
        for cls, args, kargs in Pipeline.all(log, s, type, like=like):
            log.info('Running %s (%s, %s)' % (short_cls(cls), args, kargs))
            cls(log, db).run(*args, force=force, after=after, **kargs)


def run_pipeline_paths(log, db, type, paths, force=False, like=None):
    with db.session_context() as s:
        for cls, args, kargs in Pipeline.all(log, s, type, like=like):
            log.info('Running %s (%s, %s)' % (short_cls(cls), args, kargs))
            cls(log, db).run(paths, *args, force=force, **kargs)


class Calculator:

    def __init__(self, log, db):
        self._log = log
        self._db = db


class IntervalCalculator(Calculator):
    '''
    Support for calculations associated with intervals.
    '''

    def run(self, force=False, after=None, **run_kargs):
        if force:
            self._delete(after=after, **run_kargs)
        self._run_calculations(**run_kargs)

    @abstractmethod
    def _run_calculations(self, **run_kargs):
        raise NotImplementedError()

    def _delete(self, after=None, **run_kargs):
        self._delete_intervals(after, **run_kargs)

    def _delete_intervals(self, after=None, **init_kargs):
        # we delete the intervals that all summary statistics depend on and they will cascade
        with self._db.session_context() as s:
            for repeat in range(2):
                if repeat:
                    q = s.query(Interval)
                else:
                    q = s.query(count(Interval.id))
                q = self._filter_intervals(q, **init_kargs)
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

    def _filter_intervals(self, q, **init_kargs):
        return q.filter(Interval.owner == self)


class ActivityCalculator(Calculator):
    '''
    Support for calculations associated with activity journals.
    '''

    def run(self, force=False, after=None, **run_kargs):
        with self._db.session_context() as s:
            for activity_group in s.query(ActivityGroup).all():
                self._log.debug('Checking statistics for activity %s' % activity_group.name)
                if force:
                    self._delete_my_statistics(s, activity_group, after=after, **run_kargs)
                self._run_activity(s, activity_group, **run_kargs)

    def _run_activity(self, s, activity_group, **run_kargs):
        # which activity journals don't have data?
        q1 = s.query(StatisticJournal.source_id). \
            join(StatisticName). \
            filter(StatisticName.owner == self,
                   StatisticName.constraint == activity_group)
        q1 = self._filter_journals(q1)
        statistics = q1.cte()
        q2 = s.query(ActivityJournal).outerjoin(statistics). \
                filter(ActivityJournal.activity_group == activity_group,
                       ActivityJournal.start == to_time('2017-01-18 10:39:33'),
                       statistics.c.source_id == None). \
                order_by(ActivityJournal.start)
        self._log.debug(q2)
        for ajournal in q2.all():
            self._log.info('Running %s for %s' % (short_cls(self), ajournal))
            self._add_stats(s, ajournal, **run_kargs)

    @abstractmethod
    def _filter_journals(self, q):
        raise NotImplementedError()

    @abstractmethod
    def _add_stats(self, s, ajournal, **kargs):
        raise NotImplementedError()

    def _add_float_stat(self, s, ajournal, name, summary, value, units, time=None):
        if time is None:
            time = ajournal.start
        StatisticJournalFloat.add(self._log, s, name, units, summary, self,
                                  ajournal.activity_group, ajournal, value, time)

    def _delete_my_statistics(self, s, activity_group, after=None, **run_kargs):
        '''
        Delete all statistics owned by this class and in the activity group.
        Fast because in-SQL.
        '''
        s.commit()   # so that we don't have any risk of having something in the session that can be deleted
        statistic_name_ids = s.query(StatisticName.id). \
            filter(StatisticName.owner == self).cte()
        activity_journal_ids = s.query(ActivityJournal.id). \
            filter(ActivityJournal.activity_group == activity_group).cte()
        for repeat in range(2):
            if repeat:
                q = s.query(StatisticJournal)
            else:
                q = s.query(count(StatisticJournal.id))
            q = q.filter(StatisticJournal.statistic_name_id.in_(statistic_name_ids),
                         StatisticJournal.source_id.in_(activity_journal_ids))
            if after:
                q = q.filter(StatisticJournal.time >= after)
            self._log.debug(q)
            if repeat:
                q.delete(synchronize_session=False)
            else:
                n = q.scalar()
                if n:
                    self._log.warn('Deleting %d statistics for %s' % (n, activity_group))
                else:
                    self._log.warn('No statistics to delete for %s' % activity_group)
        s.commit()


class WaypointCalculator(ActivityCalculator):

    def _add_stats(self, s, ajournal):
        waypoints = list(WaypointReader(self._log).read(s, ajournal, self._names()))
        if waypoints:
            self._add_stats_from_waypoints(s, ajournal, waypoints)
        else:
            self._log.warn('No statistics for %s' % ajournal)

    @abstractmethod
    def _add_stats_from_waypoints(self, s, ajournal, waypoints):
        raise NotImplementedError()

    @abstractmethod
    def _names(self):
        raise NotImplementedError()

