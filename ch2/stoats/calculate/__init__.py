
from abc import abstractmethod

from sqlalchemy.sql.functions import count

from ...squeal.tables.activity import ActivityJournal, ActivityGroup
from ...squeal.tables.pipeline import Pipeline
from ...squeal.tables.source import Interval, Source
from ...squeal.tables.statistic import StatisticJournal, StatisticName, StatisticJournalFloat


def run_pipeline_after(log, db, type, after=None, force=False, like=None):
    with db.session_context() as s:
        for cls, args, kargs in Pipeline.all(log, s, type, like=like):
            log.info('Running %s (%s, %s)' % (cls, args, kargs))
            cls(log, db).run(*args, force=force, after=after, **kargs)


def run_pipeline_paths(log, db, type, paths, force=False, like=None):
    with db.session_context() as s:
        for cls, args, kargs in Pipeline.all(log, s, type, like=like):
            log.info('Running %s (%s, %s)' % (cls, args, kargs))
            cls(log, db).run(paths, *args, force=force, **kargs)


class Calculator:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    @abstractmethod
    def run(self, force=False, after=None, **kargs):
        raise NotImplementedError()

    def _delete_intervals(self, after=None, **filter_kargs):
        # we delete the intervals that all summary statistics depend on and they will cascade
        with self._db.session_context() as s:
            for repeat in range(2):
                if repeat:
                    q = s.query(Interval)
                else:
                    q = s.query(count(Interval.id))
                q = self._filter_intervals(q, **filter_kargs)
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

    def _filter_intervals(self, q, **filter_kargs):
        raise NotImplementedError()


class ActivityCalculator(Calculator):

    def run(self, force=False, after=None, **kargs):
        with self._db.session_context() as s:
            for activity_group in s.query(ActivityGroup).all():
                self._log.debug('Checking statistics for activity %s' % activity_group.name)
                if force:
                    self._delete_my_statistics(s, activity_group, after=after)
                self._run_activity(s, activity_group)

    def _run_activity(self, s, activity_group, **kargs):
        # which activity journals don't have data?
        q = s.query(StatisticJournal.source_id).join(StatisticName);
        q = self._filter_journals(q)
        statistics = q.cte()
        for ajournal in s.query(ActivityJournal).outerjoin(statistics). \
                filter(ActivityJournal.activity_group == activity_group,
                       statistics.c.source_id == None). \
                order_by(ActivityJournal.start).all():
            self._log.info('Adding statistics for %s' % ajournal)
            self._add_stats(s, ajournal, **kargs)

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

    def _delete_my_statistics(self, s, activity_group, after=None):
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
