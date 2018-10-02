
import datetime as dt
from re import split

from sqlalchemy import func

from ..lib.date import add_duration, MONTH, YEAR
from ..squeal.tables.source import Interval, Source
from ..squeal.tables.statistic import StatisticJournal, Statistic, StatisticMeasure, STATISTIC_JOURNAL_CLASSES


class SummaryStatistics:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    def _delete_all(self):
        with self._db.session_context() as s:
            # we delete the intervals that all summary statistics depend on and they will cascade
            s.query(Interval).delete()

    def _raw_statistics_date_range(self, s):
        start, finish = s.query(func.min(Source.time), func.max(Source.time)). \
            join(StatisticJournal).filter(StatisticJournal.source != None).one()
        return start.date(), finish.date()

    def _intervals(self, s, duration, units):
        start, finish = self._raw_statistics_date_range(s)
        start = start.replace(day=1)
        if units == YEAR:
            start = start.replace(month=1)
        while start < finish:
            next_start = add_duration(start, (duration, units))
            yield start, next_start
            start = next_start

    def _interval(self, s, start, duration, units, days):
        interval = s.query(Interval). \
            filter(Interval.time == start,
                   Interval.value == duration,
                   Interval.units == units).one_or_none()
        if not interval:
            interval = Interval(time=start, value=duration, units=units, days=days)
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

    def _calculate_value(self, process, values):
        defined = [x for x in values if x is not None]
        if process == 'min':
            return min(defined) if defined else None, 'Min %s'
        elif process == 'max':
            return max(defined) if defined else None, 'Max %s'
        elif process == 'sum':
            return sum(defined, 0), 'Total %s'
        elif process == 'avg':
            return sum(defined) / len(defined) if defined else None, 'Avg %s'
        elif process == 'med':
            defined = sorted(defined)
            if len(defined):
                if len(defined) % 2:
                    return defined[len(defined) // 2], 'Med %s'
                else:
                    return 0.5 * (defined[len(defined) // 2 - 1] + defined[len(defined) // 2]), 'Med %s'
            else:
                return None, 'Med %s'
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

    def _create_value(self, s, interval, statistic, process, start, data, values):
        value, template = self._calculate_value(process, values)
        if value is not None:
            name = template % statistic.name
            new_statistic = self._get_statistic(s, statistic, name)
            s.add(STATISTIC_JOURNAL_CLASSES[data[0].type](
                statistic=new_statistic, source=interval, value=value))
            self._log.debug('Created %s=%s at %s' % (statistic, value, interval))

    def _create_ranks(self, s, interval, statistic, data):
        # we only rank non-NULL values
        ordered = sorted([journal for journal in data if journal.value is not None],
                         key=lambda journal: journal.value, reverse=True)
        n = len(ordered)
        for rank, journal in enumerate(ordered, start=1):
            percentile = (n - rank) / n * 100
            s.add(StatisticMeasure(statistic_journal=journal, source=interval, rank=rank, percentile=percentile))
        self._log.debug('Ranked %s' % statistic)

    def _create_values(self, duration, units):
        with self._db.session_context() as s:
            for start, finish in self._intervals(s, duration, units):
                interval = self._interval(s, start, duration, units, (finish - start).days)
                for statistic in self._statistics_missing_values(s, start, finish):
                    data = self._diary_entries(s, statistic, start, finish)
                    processes = [x for x in split(r'[\s,]*\[([^\]]+)\][\s ]*', statistic.summary) if x]
                    if processes:
                        values = [x.value for x in data]
                        for process in processes:
                            self._create_value(s, interval, statistic, process.lower(), start, data, values)
                    else:
                        self._log.warn('Invalid summary for %s ("%s")' % (statistic, statistic.summary))
                    self._create_ranks(s, interval, statistic, data)

    def run(self, force=False):
        if force:
            self._delete_all()
        for interval in (1, MONTH), (1, YEAR):
            self._create_values(*interval)

    @classmethod
    def intervals_including(cls, time):
        # this MUST match the intervals used in processing above
        yield (dt.datetime(time.year, 1, 1), (1, YEAR))
        yield (dt.datetime(time.year, time.month, 1), (1, MONTH))
