
from re import split

from sqlalchemy import func

from ..lib.date import add_duration
from ..squeal.tables.statistic import StatisticValue, Statistic, StatisticInterval, StatisticRank


class IntervalProcessing:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    def _delete_all(self):
        with self._db.session_context() as s:
            # we delete the intervals that all summary statistics depend on and they will cascade
            s.query(StatisticInterval).delete()

    def _raw_statistics_date_range(self, s):
        start, finish = s.query(func.min(StatisticValue.time), func.max(StatisticValue.time)). \
            filter(StatisticValue.statistic_diary_id == None,
                   StatisticValue.statistic_interval_id == None).one()
        return start.date(), finish.date()

    def _intervals(self, s, duration, units):
        start, finish = self._raw_statistics_date_range(s)
        start = start.replace(day=1)
        if units == 'y':
            start = start.replace(month=1)
        while start < finish:
            next_start = add_duration(start, (duration, units))
            yield start, next_start
            start = next_start

    def _interval(self, s, start, duration, units):
        interval = s.query(StatisticInterval). \
            filter(StatisticInterval.start == start,
                   StatisticInterval.value == duration,
                   StatisticInterval.units == units).one_or_none()
        if not interval:
            interval = StatisticInterval(value=duration, units=units, start=start)
            s.add(interval)
        return interval

    def _statistics_missing_values(self, s, start, finish):
        return s.query(Statistic).join(StatisticValue). \
            filter(StatisticValue.time <= start,
                   StatisticValue.time > finish,
                   Statistic.cls != self,
                   Statistic.interval_process != None).all()

    def _diary_entries(self, s, statistic, start, finish):
        return [x.value for x in
                s.query(StatisticValue).
                    filter(StatisticValue.statistic == statistic,
                           StatisticValue.time >= start,
                           StatisticValue.time < finish).all()]

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

    def _get_statistic(self, s, old_statistic, name):
        statistic = s.query(Statistic).\
            filter(Statistic.name == name,
                   Statistic.cls == self).one_or_none()
        if not statistic:
            statistic = Statistic(cls=self, cls_constraint=old_statistic.cls_constraint, name=name,
                                  units=old_statistic.units)  # todo - dsplay, sort?  encoded in process?
            s.add(statistic)
        return statistic

    def _create_value(self, s, interval, statistic, process, start, values):
        value, template =  self._calculate_value(process, values)
        name = template % statistic.name
        new_statistic = self._get_statistic(s, name)
        s.add(StatisticValue(statistic=new_statistic, value=value, time=start, interval=interval))
        self._log.debug('Created %s=%s at %s' % (statistic, value, interval))

    def _create_ranks(self, s, interval, statistic, data):
        # we only rank non-NULL values
        ordered = sorted([x for x in data if x.value is not None], key=lambda x: x.value, reverse=True)
        n = len(ordered)
        for rank, x in enumerate(ordered, start=1):
            percentile = (n - rank) / n * 100
            s.add(StatisticRank(diary=x, interval=interval, rank=rank, percentile=percentile))
        self._log.debug('Ranked %s' % statistic)

    def _create_values(self, duration, units):
        with self._db.session_context() as s:
            for start, finish in self._intervals(s, duration, units):
                interval = self._interval(s, start, duration, units)
                for statistic in self._statistics_missing_values(s, start, finish):
                    data = self._diary_entries(s, statistic, start, finish)
                    processes = split(r'[\s,]*\[([^\]])\][\s ]*', statistic.interval_process)
                    if processes:
                        values = [x.value for x in data]
                        for process in processes:
                            self._create_value(s, interval, statistic, process.lower(), start, values)
                    else:
                        self._log.warn('No valid process for %s ("%s")' % (statistic, statistic.interval_process))
                    self._create_ranks(s, interval, statistic, data)

    def run(self, force=False):
        if force:
            self._delete_all()
        for interval in (1, 'm'), (1, 'y'):
            self._create_values(*interval)
