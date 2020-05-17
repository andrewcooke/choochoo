
from logging import getLogger

from .utils import Displayer
from ..calculate.monitor import MonitorCalculator
from ...names import Names
from ...diary.database import summary_column
from ...diary.model import value, optional_text
from ...sql.tables.statistic import StatisticJournal, StatisticName

log = getLogger(__name__)


class MonitorDisplayer(Displayer):

    @optional_text('Monitor')
    def _read_date(self, s, date):
        for field in self.__read_fields(s, date, Names.DAILY_STEPS, Names.REST_HR):
            yield value(field.statistic_name.title, field.value,
                        units=field.statistic_name.units, measures=field.measures_as_model(date))

    @staticmethod
    def __read_fields(s, date, *names):
        for name in names:
            journal = StatisticJournal.at_date(s, date, name, MonitorCalculator, None)
            if journal:
                yield journal

    @optional_text('Monitor')
    def _read_schedule(self, s, date, schedule):
        for name in self.__names(s, Names.DAILY_STEPS, Names.REST_HR):
            column = list(summary_column(s, schedule, date, name))
            if column:
                yield column

    @staticmethod
    def __names(s, *names):
        for name in names:
            sname = s.query(StatisticName). \
                filter(StatisticName.name == name,
                       StatisticName.owner == MonitorCalculator).one_or_none()
            if sname:
                yield sname
