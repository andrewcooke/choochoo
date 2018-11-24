
from random import choice
from re import split

from sqlalchemy import func, inspect, and_, select
from sqlalchemy.sql.functions import coalesce

from . import IntervalCalculator
from ..names import MAX, MIN, SUM, CNT, AVG, MSR, ENTRIES
from ...lib.date import local_date_to_time
from ...lib.schedule import Schedule
from ...squeal.database import add
from ...squeal.tables.source import Interval
from ...squeal.tables.statistic import StatisticJournal, StatisticName, StatisticMeasure, STATISTIC_JOURNAL_CLASSES, \
    StatisticJournalType, StatisticJournalInteger, StatisticJournalFloat, StatisticJournalText


TYPE_TO_JOURNAL_TYPE = {
    int: StatisticJournalType.INTEGER,
    float: StatisticJournalType.FLOAT,
    str: StatisticJournalType.TEXT,
    type(None): None
}


class SummaryStatistics(IntervalCalculator):

    def run(self, force=False, after=None, schedule=None):
        if not schedule:
            raise Exception('schedule=... karg required')
        schedule = Schedule(schedule)
        super().run(force=force, after=after, schedule=schedule)

    def _filter_intervals(self, q, schedule=None):
        return q.filter(Interval.schedule == schedule,
                        Interval.owner == self)

    def _statistics_missing_summaries(self, s, start, finish):
        statistics_with_data_but_no_summary = s.query(StatisticName.id). \
            join(StatisticJournal). \
            filter(StatisticJournal.time >= start,
                   StatisticJournal.time < finish,
                   StatisticName.summary != None)
        # avoid duplicates
        return s.query(StatisticName). \
            filter(StatisticName.id.in_(statistics_with_data_but_no_summary)). \
            all()

    def _calculate_value(self, s, statistic_name, summary, start_time, finish_time, schedule):

        range = schedule.describe()
        units = statistic_name.units

        sj = inspect(StatisticJournal).local_table
        sji = inspect(StatisticJournalInteger).local_table
        sjf = inspect(StatisticJournalFloat).local_table
        sjt = inspect(StatisticJournalText).local_table

        values = coalesce(sjf.c.value, sji.c.value, sjt.c.value)

        if summary == MAX:
            result = func.max(values)
        elif summary == MIN:
            result = func.min(values)
        elif summary == SUM:
            result = func.sum(values)
        elif summary == CNT:
            result = func.count(values)
            units = ENTRIES;
        elif summary == AVG:
            result = func.avg(values)
        elif summary == MSR:
            return None, None, None, None
        else:
            raise Exception('Bad summary: %s' % summary)

        stmt = select([result]). \
            select_from(sj.outerjoin(sjf).outerjoin(sji).outerjoin(sjt)). \
            where(and_(sj.c.statistic_name_id == statistic_name.id,
                       sj.c.time >= start_time,
                       sj.c.time < finish_time))

        value = next(s.connection().execute(stmt))[0]
        title = summary[1:-1].capitalize()
        return value, '%s/%s %%s' % (title, range), TYPE_TO_JOURNAL_TYPE[type(value)], units

    def _create_value(self, s, statistic_name, summary, start_time, finish_time, interval, schedule):
        value, template, type, units = self._calculate_value(s, statistic_name, summary, start_time, finish_time,
                                                             schedule)
        if value is not None:
            name = template % statistic_name.name
            new_name = StatisticName.add_if_missing(self._log, s, name, units, None, self, statistic_name)
            journal = add(s, STATISTIC_JOURNAL_CLASSES[type](
                statistic_name=new_name, source=interval, value=value, time=start_time))
            self._log.debug('Created %s over %s for %s' % (journal, interval, statistic_name))
        return bool(value)

    def _create_measures(self, s, statistic_name, start_time, finish_time, interval):

        data = sorted([x for x in
                       s.query(StatisticJournal).
                      filter(StatisticJournal.statistic_name == statistic_name,
                             StatisticJournal.time >= start_time,
                             StatisticJournal.time < finish_time).all()
                       if x is not None], key=lambda x: x.value)

        # todo - asc/desc

        n, measures = len(data), []
        for rank, journal in enumerate(data, start=1):
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
        self._log.debug('Ranked %s' % statistic_name)

    def _run_calculations(self, schedule):
        with self._db.session_context() as s:
            for start, finish in Interval.missing_dates(self._log, s, schedule, self):
                start_time, finish_time = local_date_to_time(start), local_date_to_time(finish)
                interval = add(s, Interval(start=start, finish=finish, schedule=schedule, owner=self))
                have_data = False
                for statistic_name in self._statistics_missing_summaries(s, start_time, finish_time):
                    self._log.debug(statistic_name)
                    summaries = [x.lower() for x in split(r'[\s,]*(\[[^\]]+\])[\s ]*', statistic_name.summary) if x]
                    for summary in summaries:
                        have_data |= self._create_value(s, statistic_name, summary, start_time, finish_time, interval,
                                                        schedule)
                    if MSR in summaries:
                        self._create_measures(s, statistic_name, start_time, finish_time, interval)
                if have_data:
                    self._log.info('Added statistics for %s' % interval)
                else:
                    s.delete(interval)

    @classmethod
    def parse_name(cls, name):
        left, right = name.split(' ', 1)
        summary, period = left.split('/')
        return summary, period, right


def fuzz(n, q):
    i = (n-1) * q / 4
    if i != int(i):
        i = int(i) + choice([0, 1])  # if we're between two points, pick either
    return int(i)
