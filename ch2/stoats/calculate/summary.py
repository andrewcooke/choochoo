
from random import choice
from re import split

from sqlalchemy import func
from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import count

from ch2.squeal.database import add
from ...lib.date import to_date
from ...lib.schedule import Schedule
from ...squeal.tables.pipeline import Pipeline, PipelineType
from ...squeal.tables.source import Interval, Source
from ...squeal.tables.statistic import StatisticJournal, Statistic, StatisticMeasure, STATISTIC_JOURNAL_CLASSES, \
    StatisticType


class SummaryStatistics:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    def run(self, schedule=None, force=False, after=None):
        if schedule is None:
            for schedule in self._pipeline_schedules():
                self._run_schedule(schedule, force, after=after)
        else:
            self._run_schedule(Schedule(schedule), force, after=after)

    def _pipeline_schedules(self):
        with self._db.session_context() as s:
            return [Schedule(spec) for spec in self.pipeline_schedules(s)]

    @classmethod
    def pipeline_schedules(cls, s):
        for kargs in s.query(Pipeline.kargs). \
                filter(Pipeline.cls == cls,
                       Pipeline.type == PipelineType.STATISTIC).all():
            if 'schedule' in kargs[0]:
                yield kargs[0]['schedule']
            else:
                raise Exception('No schedule in kargs for Statistic Pipeline (%s)' % cls.__name__)

    def _run_schedule(self, spec, force, after=None):
        if force:
            self._delete(spec, after)
        self._create_values(spec)

    def _delete(self, spec, after=None):
        # we delete the intervals that summary statistics depend on and they will cascade
        with self._db.session_context() as s:
            for repeat in range(2):
                if repeat:
                    q = s.query(Interval)
                else:
                    q = s.query(count(Interval.id))
                q = q.filter(Interval.schedule == spec,
                             Interval.owner == self)
                if after:
                    q = q.filter(Interval.finish > after)
                if repeat:
                    for interval in q.all():
                        self._log.debug('Deleting %s' % interval)
                        s.delete(interval)
                else:
                    n = q.scalar()
                    if n:
                        self._log.info('Deleting %d intervals' % n)
                    else:
                        self._log.warn('No intervals to delete')

    def _statistics_missing_summaries(self, s, start, finish):
        statistics_with_data_but_no_summary = s.query(Statistic.id). \
            join(StatisticJournal, Source). \
            filter(Source.time >= start,
                   Source.time < finish,
                   Statistic.summary != None)
        return s.query(Statistic). \
            filter(Statistic.id.in_(statistics_with_data_but_no_summary)). \
            all()

    def _diary_entries(self, s, statistic, start, finish):
        return s.query(StatisticJournal).join(Source). \
            filter(StatisticJournal.statistic == statistic,
                   Source.time >= start,
                   Source.time < finish).all()

    def _calculate_value(self, process, values, schedule, input_type):
        range = schedule.describe()
        defined = [x for x in values if x is not None]
        if process == 'min':
            return min(defined) if defined else None, 'Min/%s %%s' % range, input_type
        elif process == 'max':
            return max(defined) if defined else None, 'Max/%s %%s' % range, input_type
        elif process == 'sum':
            return sum(defined, 0), 'Total/%s %%s' % range, input_type
        elif process == 'avg':
            return sum(defined) / len(defined) if defined else None, 'Avg/%s %%s' % range, StatisticType.FLOAT
        elif process == 'med':
            defined = sorted(defined)
            if len(defined):
                if len(defined) % 2:
                    return defined[len(defined) // 2], 'Med/%s %%s' % range, StatisticType.FLOAT
                else:
                    return 0.5 * (defined[len(defined) // 2 - 1] + defined[len(defined) // 2]), \
                           'Med/%s %%s' % range, StatisticType.FLOAT
            else:
                return None, 'Med/%s %%s' % range, StatisticType.FLOAT
        else:
            self._log.warn('No algorithm for "%s"' % process)
            return None, None, None

    def _get_statistic(self, s, root, name):
        # we use the old statistic id as the constraint.  this lets us handle multiple
        # statistics with the same name, but different owners and constraints.
        statistic = s.query(Statistic). \
            filter(Statistic.name == name,
                   Statistic.owner == self,
                   Statistic.constraint == root.id).one_or_none()
        if not statistic:
            statistic = add(s, Statistic(name=name, owner=self, constraint=root.id, units=root.units))
        return statistic

    def _create_value(self, s, interval, spec, statistic, process, data, values):
        value, template, type = self._calculate_value(process, values, spec, data[0].type)
        if value is not None:
            name = template % statistic.name
            new_statistic = self._get_statistic(s, statistic, name)
            journal = add(s, STATISTIC_JOURNAL_CLASSES[type](
                statistic=new_statistic, source=interval, value=value))
            self._log.debug('Created %s over %s for %s' % (journal, interval, statistic))

    def _create_ranks(self, s, interval, spec, statistic, data):
        # we only rank non-NULL values
        ordered = sorted([journal for journal in data if journal.value is not None],
                         key=lambda journal: journal.value, reverse=True)
        n, measures = len(ordered), []
        for rank, journal in enumerate(ordered, start=1):
            if n > 1:
                percentile = (n - rank) / (n - 1) * 100
            else:
                percentile = 100
            measure = StatisticMeasure(statistic_journal=journal, source=interval, rank=rank, percentile=percentile)
            s.add(measure)
            measures.append(measure)
        if n > 8:  # avoid overlap in fuzzing (and also, plot individual points in this case)
            for q in range(5):
                measures[fuzz(n, q)].quartile = q
        self._log.debug('Ranked %s' % statistic)

    def _create_values(self, spec):
        with self._db.session_context() as s:
            for start, finish in Interval.missing(self._log, s, spec, self):
                interval = add(s, Interval(time=start, finish=finish, schedule=spec, owner=self))
                have_data = False
                for statistic in self._statistics_missing_summaries(s, start, finish):
                    data = [journal for journal in self._diary_entries(s, statistic, start, finish)
                            if spec.at_location(to_date(journal.time))]
                    if data:
                        processes = [x for x in split(r'[\s,]*\[([^\]]+)\][\s ]*', statistic.summary) if x]
                        if processes:
                            values = [x.value for x in data]
                            for process in processes:
                                self._create_value(s, interval, spec, statistic, process.lower(), data, values)
                        else:
                            self._log.warn('Invalid summary for %s ("%s")' % (statistic, statistic.summary))
                        self._create_ranks(s, interval, spec, statistic, data)
                        have_data = True
                if have_data:
                    self._log.info('Added statistics for %s' % interval)
                else:
                    s.delete(interval)


def fuzz(n, q):
    i = (n-1) * q / 4
    if i != int(i):
        i = int(i) + choice([0, 1])  # if we're between two points, pick either
    return int(i)
