
from logging import getLogger
from random import choice

from sqlalchemy import func, inspect, and_, select
from sqlalchemy.sql.functions import coalesce

from .calculate import MultiProcCalculator, IntervalCalculatorMixin
from ...names import Summaries as S
from ...lib.date import local_date_to_time
from ...sql.tables.source import Interval
from ...sql.tables.statistic import StatisticJournal, StatisticName, StatisticMeasure, StatisticJournalInteger, \
    StatisticJournalFloat, StatisticJournalText, TYPE_TO_JOURNAL_CLASS

log = getLogger(__name__)


def fuzz(n, q):
    # n is number of points, q is quartile (0-4).
    # return index for quartile that is unbiased when location not exact
    i = (n-1) * q / 4
    if i != int(i):
        i = int(i) + choice([0, 1])  # if we're between two points, pick either
    return int(i)


class SummaryCalculator(IntervalCalculatorMixin, MultiProcCalculator):

    def _startup(self, s):
        Interval.clean(s)

    def _read_data(self, s, interval):
        # here, data is only statistics names, because calculation also involves loading data
        start, finish = local_date_to_time(interval.start), local_date_to_time(interval.finish)
        statistics_with_data_and_summary = s.query(StatisticName.id). \
            join(StatisticJournal). \
            filter(StatisticJournal.time >= start,
                   StatisticJournal.time < finish,
                   StatisticName.summary != None)
        # avoid duplicates
        return s.query(StatisticName). \
            filter(StatisticName.id.in_(statistics_with_data_and_summary)).all()

    def _calculate_results(self, s, interval, data, loader):
        start, finish = local_date_to_time(interval.start), local_date_to_time(interval.finish)
        measures = []
        for statistic_name in data:
            summaries = statistic_name.summaries
            for summary in summaries:
                value, units = self._calculate_value(s, statistic_name, summary, S.MIN in summaries,
                                                     start, finish, interval, measures)
                if value is not None:
                    title = self.fmt_title(statistic_name.title, summary, self.schedule)
                    # we need to infer the type
                    if summary in (S.MAX, S.MIN, S.SUM):
                        new_type = TYPE_TO_JOURNAL_CLASS[type(value)]
                    elif summary in (S.AVG,):
                        new_type = StatisticJournalFloat
                    else:
                        new_type = StatisticJournalInteger
                    loader.add(title, units, None, statistic_name.activity_group, interval, value, start, new_type,
                               description=self._describe(statistic_name, summary, interval))
        # add and commit these here - what else can we do?
        log.debug(f'Adding {len(measures)} measures')
        for measure in measures:
            s.add(measure)
        s.commit()

    def _calculate_value(self, s, statistic_name, summary, order_asc, start_time, finish_time, interval, measures):

        sj = inspect(StatisticJournal).local_table
        sji = inspect(StatisticJournalInteger).local_table
        sjf = inspect(StatisticJournalFloat).local_table
        sjt = inspect(StatisticJournalText).local_table

        units = statistic_name.units
        values = coalesce(sjf.c.value, sji.c.value, sjt.c.value)

        if summary == S.MAX:
            result = func.max(values)
        elif summary == S.MIN:
            result = func.min(values)
        elif summary == S.SUM:
            result = func.sum(values)
        elif summary == S.CNT:
            result = func.count(values)
            units = None
        elif summary == S.AVG:
            result = func.avg(values)
        elif summary == S.MSR:
            self._calculate_measures(s, statistic_name, order_asc, start_time, finish_time, interval, measures)
            return None, None
        else:
            raise Exception('Bad summary: %s' % summary)

        stmt = select([result]). \
            select_from(sj.outerjoin(sjf).outerjoin(sji).outerjoin(sjt)). \
            where(and_(sj.c.statistic_name_id == statistic_name.id,
                       sj.c.time >= start_time,
                       sj.c.time < finish_time))

        return next(s.connection().execute(stmt))[0], units

    def _describe(self, statistic_name, summary, interval):
        adjective = {S.MAX: 'highest', S.MIN: 'lowest', S.SUM: 'total', S.CNT: 'number of', S.AVG: 'average'}[summary]
        period = interval.schedule.describe().lower()
        if period == 'all':
            period = period + ' time'
        else:
            period = 'one ' + period
        return f'The {adjective} {statistic_name.title} over {period}.'

    def _calculate_measures(self, s, statistic_name, order_asc, start_time, finish_time, interval, measures):
        data = sorted([x for x in
                       s.query(StatisticJournal).
                           filter(StatisticJournal.statistic_name == statistic_name,
                                 StatisticJournal.time >= start_time,
                                 StatisticJournal.time < finish_time).all()
                       if x is not None and x.value is not None],
                      key=lambda x: x.value, reverse=not order_asc)
        n, local_measures = len(data), []
        for rank, journal in enumerate(data, start=1):
            if n > 1:
                percentile = (n - rank) / (n - 1) * 100
            else:
                percentile = 100
            measure = StatisticMeasure(statistic_journal=journal, source=interval, rank=rank, percentile=percentile)
            local_measures.append(measure)
            measures.append(measure)
        if n > 8:  # avoid overlap in fuzzing (and also, plot individual points in this case)
            for q in range(5):
                local_measures[fuzz(n, q)].quartile = q
        log.debug('Ranked %s' % statistic_name)

    @classmethod
    def parse_title(cls, name):
        left, right = name.split(' ', 1)
        summary, period = left.split('/')
        return summary, period, right

    @classmethod
    def fmt_title(cls, name, summary, schedule):
        title = summary.capitalize()
        return '%s/%s %s' % (title, schedule.describe(), name)
