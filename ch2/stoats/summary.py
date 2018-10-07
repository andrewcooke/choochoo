
from random import choice
from re import split

from sqlalchemy import func
from sqlalchemy.sql.functions import count

from ..lib.date import add_duration
from ..lib.schedule import Specification
from ..squeal.tables.source import Interval, Source
from ..squeal.tables.statistic import StatisticJournal, Statistic, StatisticMeasure, STATISTIC_JOURNAL_CLASSES, \
    StatisticPipeline


class SummaryStatistics:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    def run(self, spec=None, force=False, after=None):
        if spec is None:
            for spec in self._pipeline_specs():
                self._run(spec, force, after)
        else:
            self._run(Specification(spec), force, after=None)

    def _run(self, spec, force, after=None):
        if force:
            self._delete(spec, after)
        self._create_values(spec)

    def _pipeline_specs(self):
        with self._db.session_context() as s:
            return [Specification(spec) for spec in self.pipeline_specs(s)]

    @classmethod
    def pipeline_specs(cls, s):
        for kargs in s.query(StatisticPipeline.kargs).filter(StatisticPipeline.cls == cls).all():
            if 'spec' in kargs[0]:
                yield kargs[0]['spec']
            else:
                raise Exception('No spec in kargs for Statistic Pipeline (%s)' % cls.__name__)

    def _delete(self, spec, after=None):
        # we delete the intervals that all summary statistics depend on and they will cascade
        with self._db.session_context() as s:
            for repeat in range(2):
                if repeat:
                    q = s.query(Interval)
                else:
                    q = s.query(count(Interval.id))
                q = q.filter(Interval.spec == spec)
                if after:
                    q.q.filter(Interval.finish > after)
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

    def _raw_statistics_date_range(self, s):
        start, finish = s.query(func.min(Source.time), func.max(Source.time)). \
            join(StatisticJournal).filter(StatisticJournal.source != None).one()
        if start and finish:
            return start.date(), finish.date()
        else:
            raise Exception('No statistics are currently defined')

    def _intervals(self, s, spec):
        start, finish = self._raw_statistics_date_range(s)
        start = spec.frame().start(start)
        while start <= finish:
            next_start = add_duration(start, (spec.repeat, spec.duration))
            yield start, next_start
            start = next_start

    def _interval(self, s, start, finish, spec):
        interval = s.query(Interval). \
            filter(Interval.time == start,
                   Interval.spec == spec,
                   Interval.finish == finish).one_or_none()
        if not interval:
            interval = Interval(time=start, finish=finish, spec=spec)
            s.add(interval)
        return interval

    def _statistics_missing_values(self, s, start, finish):
        return s.query(Statistic).join(StatisticJournal, Source). \
            filter(Source.time >= start,
                   Source.time < finish,
                   Statistic.summary != None).all()

    def _diary_entries(self, s, statistic, start, finish):
        return s.query(StatisticJournal).join(Source). \
            filter(StatisticJournal.statistic == statistic,
                   Source.time >= start,
                   Source.time < finish).all()

    def _calculate_value(self, process, values, spec):
        range = {'d': 'Day', 'w': 'Week', 'm': 'Month', 'y': 'Year'}[spec.frame_type]
        if spec.repeat > 1:
            range = '%d%ss' % (spec.repeat, range)
        defined = [x for x in values if x is not None]
        if process == 'min':
            return min(defined) if defined else None, 'Min/%s %%s' % range
        elif process == 'max':
            return max(defined) if defined else None, 'Max/%s %%s' % range
        elif process == 'sum':
            return sum(defined, 0), 'Total/%s %%s' % range
        elif process == 'avg':
            return sum(defined) / len(defined) if defined else None, 'Avg/%s %%s' % range
        elif process == 'med':
            defined = sorted(defined)
            if len(defined):
                if len(defined) % 2:
                    return defined[len(defined) // 2], 'Med/%s %%s' % range
                else:
                    return 0.5 * (defined[len(defined) // 2 - 1] + defined[len(defined) // 2]), 'Med/%s %%s' % range
            else:
                return None, 'Med/%s %%s' % range
        else:
            self._log.warn('No algorithm for "%s"' % process)
            return None, None

    def _get_statistic(self, s, root, name):
        statistic = s.query(Statistic). \
            filter(Statistic.name == name,
                   Statistic.owner == self).one_or_none()
        if not statistic:
            statistic = Statistic(name=name, owner=self, units=root.units)
            s.add(statistic)
        return statistic

    def _create_value(self, s, interval, spec, statistic, process, data, values):
        value, template = self._calculate_value(process, values, spec)
        if value is not None:
            name = template % statistic.name
            new_statistic = self._get_statistic(s, statistic, name)
            journal = STATISTIC_JOURNAL_CLASSES[data[0].type](
                statistic=new_statistic, source=interval, value=value)
            s.add(journal)
            self._log.debug('Created %s over %s for %s' % (journal, interval, statistic))

    def _create_ranks(self, s, interval, statistic, data):
        # we only rank non-NULL values
        ordered = sorted([journal for journal in data if journal.value is not None],
                         key=lambda journal: journal.value, reverse=True)
        n, measures = len(ordered), []
        for rank, journal in enumerate(ordered, start=1):
            percentile = (n - rank) / n * 100
            measure = StatisticMeasure(statistic_journal=journal, source=interval, rank=rank, percentile=percentile)
            s.add(measure)
            measures.append(measure)
        if n > 8:  # avoid overlap in fuzzing (and also, plot individual points in this case)
            for q in range(5):
                measures[fuzz(n, q)].quartile = q
        self._log.debug('Ranked %s' % statistic)

    def _create_values(self, spec):
        with self._db.session_context() as s:
            for start, finish in self._intervals(s, spec):
                interval = self._interval(s, start, finish, spec)
                self._log.info('Adding statistics for %s' % interval)
                for statistic in self._statistics_missing_values(s, start, finish):
                    data = self._diary_entries(s, statistic, start, finish)
                    processes = [x for x in split(r'[\s,]*\[([^\]]+)\][\s ]*', statistic.summary) if x]
                    if processes:
                        values = [x.value for x in data]
                        for process in processes:
                            self._create_value(s, interval, spec, statistic, process.lower(), data, values)
                    else:
                        self._log.warn('Invalid summary for %s ("%s")' % (statistic, statistic.summary))
                    self._create_ranks(s, interval, statistic, data)


def fuzz(n, q):
    i = (n-1) * q / 4
    if i != int(i):
        i = int(i) + choice([0, 1])  # if we're between two points, pick either
    return int(i)
