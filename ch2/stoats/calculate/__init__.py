
from abc import abstractmethod

from sqlalchemy.sql.functions import count

from .. import DbPipeline
from ..waypoint import WaypointReader
from ...lib.schedule import Schedule
from ...squeal.tables.activity import ActivityJournal, ActivityGroup
from ...squeal.tables.pipeline import Pipeline
from ...squeal.tables.source import Interval
from ...squeal.tables.statistic import StatisticJournal, StatisticName, StatisticJournalFloat
from ...squeal.types import short_cls


def run_pipeline_after(log, db, type, after=None, force=False, like=None):
    with db.session_context() as s:
        for cls, args, kargs in Pipeline.all(log, s, type, like=like):
            log.info('Running %s (%s, %s)' % (short_cls(cls), args, kargs))
            cls(log, db, *args, **kargs).run(force=force, after=after)


def run_pipeline_paths(log, db, type, paths, force=False, like=None):
    with db.session_context() as s:
        for cls, args, kargs in Pipeline.all(log, s, type, like=like):
            log.info('Running %s (%s, %s)' % (short_cls(cls), args, kargs))
            cls(log, db, *args, **kargs).run(paths, force=force)


class IntervalCalculator(DbPipeline):
    '''
    Support for calculations associated with intervals.
    '''

    def run(self, force=False, after=None):
        schedule = Schedule(self._assert_karg('schedule'))
        self.run_schedule(force=force, after=after, schedule=schedule)

    def run_schedule(self, force=False, after=None, schedule=None):
        if force:
            self._delete(after=after)
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
    Support for calculations associated with activity journals.
    '''

    def run(self, force=False, after=None):
        with self._db.session_context() as s:
            for activity_group in s.query(ActivityGroup).all():
                self._log.debug('Checking statistics for activity %s' % activity_group.name)
                if force:
                    self._delete_my_statistics(s, activity_group, after=after)
                self._run_activity(s, activity_group)

    def _run_activity(self, s, activity_group):
        # which activity journals don't have data?
        q1 = s.query(StatisticJournal.source_id). \
            join(StatisticName). \
            filter(StatisticName.owner == self,
                   StatisticName.constraint == activity_group)
        q1 = self._filter_statistic_journals(q1)
        statistics = q1.cte()
        q2 = s.query(ActivityJournal). \
            outerjoin(statistics). \
            filter(ActivityJournal.activity_group == activity_group,
                   statistics.c.source_id == None)
        for ajournal in q2.order_by(ActivityJournal.start).all():
            self._log.info('Running %s for %s' % (short_cls(self), ajournal))
            self._add_stats(s, ajournal)

    @abstractmethod
    def _filter_statistic_journals(self, q):
        raise NotImplementedError()

    @abstractmethod
    def _add_stats(self, s, ajournal):
        raise NotImplementedError()

    def _add_float_stat(self, s, ajournal, name, summary, value, units, time=None):
        if time is None:
            time = ajournal.start
        StatisticJournalFloat.add(self._log, s, name, units, summary, self,
                                  ajournal.activity_group, ajournal, value, time)

    def _delete_my_statistics(self, s, agroup, after=None):
        '''
        Delete all statistics owned by this class and in the activity group.
        Fast because in-SQL.
        '''
        s.commit()   # so that we don't have any risk of having something in the session that can be deleted
        for repeat in range(2):
            cte = s.query(StatisticName.id).filter(StatisticName.owner == self)
            if repeat:
                q = s.query(StatisticJournal)
            else:
                q = s.query(count(StatisticJournal.id))
            q = q.filter(StatisticJournal.statistic_name_id.in_(cte.cte()))
            q = self._constrain_group(s, q, agroup)
            if after:
                q = q.filter(StatisticJournal.time >= after)
            if repeat:
                q.delete(synchronize_session=False)
            else:
                n = q.scalar()
                if n:
                    self._log.warning('Deleting %d statistics for %s' % (n, agroup))
                else:
                    self._log.warning('No statistics to delete for %s' % agroup)
        s.commit()

    def _constrain_group(self, s, q, agroup):
        cte = s.query(ActivityJournal.id).filter(ActivityJournal.activity_group_id == agroup.id).cte()
        return q.filter(StatisticJournal.source_id.in_(cte))


class WaypointCalculator(ActivityCalculator):

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

