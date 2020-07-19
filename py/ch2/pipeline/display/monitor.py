
from logging import getLogger

from .utils import Displayer
from ..calculate import SummaryCalculator
from ..calculate.monitor import StepsCalculator
from ...names import N
from ...diary.database import summary_column, interval_column
from ...diary.model import value, optional_text
from ...sql import Interval
from ...sql.tables.statistic import StatisticJournal, StatisticName

log = getLogger(__name__)


class MonitorDisplayer(Displayer):

    @optional_text('Monitor')
    def _read_date(self, s, date):
        for field in self.__read_fields(s, date, N.DAILY_STEPS, N.REST_HR):
            yield value(field.statistic_name.title, field.value,
                        units=field.statistic_name.units, measures=field.measures_as_model(date))

    @staticmethod
    def __read_fields(s, date, *names):
        for name in names:
            journal = StatisticJournal.at_date(s, date, name, StepsCalculator, None)
            if journal:
                yield journal

    @optional_text('Monitor')
    def _read_schedule(self, s, date, schedule):
        interval = s.query(Interval). \
            filter(Interval.schedule == schedule,
                   Interval.start == date,
                   Interval.activity_group == None).one_or_none()
        for name in (N.DAILY_STEPS, N.REST_HR):
            column = list(interval_column(s, interval, name, SummaryCalculator))
            if column: yield column
