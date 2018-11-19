
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

    def run(self, force=False, after=None):
        with self._db.session_context() as s:
            for activity_group in s.query(ActivityGroup).all():
                self._log.debug('Checking statistics for activity %s' % activity_group.name)
                if force:
                    self._delete_statistics(s, activity_group, after=after)
                self._run_activity(s, activity_group)

    def _run_activity(self, s, activity_group):
        # which activity journals don't have data?
        q = s.query(StatisticJournal.source_id).join(StatisticName);
        q = self._filter_journals(q)
        statistics = q.cte()
        for ajournal in s.query(ActivityJournal).outerjoin(statistics). \
                filter(ActivityJournal.activity_group == activity_group,
                       statistics.c.source_id == None). \
                order_by(ActivityJournal.start).all():
            self._log.info('Adding statistics for %s' % ajournal)
            self._add_stats(s, ajournal)

    @abstractmethod
    def _filter_journals(self, q):
        raise NotImplementedError()

    @abstractmethod
    def _add_stats(self, s, ajournal):
        raise NotImplementedError()

    def _add_float_stat(self, s, ajournal, name, summary, value, units, time=None):
        if time is None:
            time = ajournal.start
        StatisticJournalFloat.add(self._log, s, name, units, summary, self,
                                  ajournal.activity_group, ajournal, value, time)

    def _delete_statistics(self, s, activity_group, after=None):
        # we can't delete the source because that's the activity journal
        # (and we're calculating here, not importing)
        # so instead we wipe all statistics that are owned by us.
        # we do this in SQL for speed, but are careful to use the parent node.
        for repeat in range(2):
            if repeat:
                q = s.query(StatisticJournal)
            else:
                q = s.query(count(StatisticJournal.id))
            q = q.join(StatisticName, Source, ActivityJournal). \
                filter(StatisticName.owner == self,
                       ActivityJournal.activity_group == activity_group)
            if after:
                q = q.filter(StatisticJournal.time >= after)
            if repeat:
                for journal in q.all():
                    # self._log.debug('Deleting %s (%s)' % (journal, journal.statistic_name))
                    s.delete(journal)
            else:
                n = q.scalar()
                if n:
                    self._log.warn('Deleting %d statistics for %s' % (n, activity_group))
                else:
                    self._log.warn('No statistics to delete for %s' % activity_group)


