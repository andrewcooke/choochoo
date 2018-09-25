
from sqlalchemy import func

from ..lib.date import add_duration
from ..squeal.tables.statistic import StatisticDiary, Statistic, StatisticInterval


class IntervalStatistics:

    def __init__(self, log, db):
        self.__log = log
        self.__db = db

    def delete_all(self):
        with self.__db.session_context() as s:
            # we delete the intervals that all summary statistics depend on and they will cascade
            s.query(StatisticInterval).delete()

    def __raw_statistics_date_range(self, s):
        start, finish = s.query(func.min(StatisticDiary.time), func.max(StatisticDiary.time)). \
            filter(StatisticDiary.depends_on_id == None).one()
        return start.date(), finish.date()

    def __intervals(self, s, duration, units):
        start, finish = self.__raw_statistics_date_range(s)
        start = start.replace(day=1)
        if units == 'y':
            start = start.replace(month=1)
        while start < finish:
            next_start = add_duration(start, (duration, units))
            yield start, next_start
            start = next_start

    def __interval(self, s, start, duration, units):
        interval = s.query(StatisticInterval).filter(StatisticInterval.start == start,
                                                     StatisticInterval.value == duration,
                                                     StatisticInterval.units == units).one_or_none()
        if not interval:
            interval = StatisticInterval(value=duration, units=units, start=start)
            s.add(interval)
        return interval

    def __current_statistics(self, s, start, finish):
        s.query(Statistic).join(StatisticDiary). \
            filter(StatisticDiary.time <= start,
                   StatisticDiary.time > finish,
                   Statistic.cls != self)

    def create_summaries(self, duration, units):
        with self.__db.session_context() as s:
            for start, finish in self.__intervals(s, duration, units):
                interval = self.__interval(s, start, duration, units)
                for statistic in self.__current_statistics(s, start, finish):
                    self.__create_summary(s, statistic)

    def create_all(self, force=False):
        if force:
            self.delete_all()
        for interval in (1, 'm'), (1, 'y'):
            create_summaries(*interval)
            create_yearly_ranks(*interval)
