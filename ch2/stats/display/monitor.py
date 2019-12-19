
from logging import getLogger

from urwid import Text, Columns, Pile

from . import Displayer, Reader
from ..calculate.monitor import MonitorCalculator
from ..names import REST_HR, DAILY_STEPS
from ...diary.model import value, text
from ...sql.tables.statistic import StatisticJournal, StatisticName
from ...urwid.fields import ReadOnlyField
from ...urwid.fields.summary import summary_columns
from ...urwid.tui.decorators import Indent

log = getLogger(__name__)


class MonitorDiary(Displayer, Reader):

    def _display_date(self, s, f, date):
        columns = self.__fields(s, date)
        if columns:
            yield Pile([Text('Monitor'),
                        Indent(Columns(columns))])

    def _read_date(self, s, date):
        first = True
        for field in self.__read_fields(s, date, DAILY_STEPS, REST_HR):
            if first:
                yield text('Monitor')
                first = False
            yield value(field.statistic_name.name, field.value,
                        units=field.statistic_name.units, measures=field.measures_as_model(date))

    def __fields(self, s, date):
        fields = list(self.__read_fields(s, date, DAILY_STEPS, REST_HR))
        if fields:
            return [ReadOnlyField(field, date=date).widget() for field in fields]
        else:
            return None

    def __read_fields(self, s, date, *names):
        for name in names:
            journal = StatisticJournal.at_date(s, date, name, MonitorCalculator, None)
            if journal: yield journal

    def _display_schedule(self, s, f, date, schedule):
        columns = list(self.__schedule_fields(s, f, date, schedule))
        if columns:
            yield Pile([Text('Monitor'),
                        Indent(Pile(columns))])

    def __schedule_fields(self, s, f, date, schedule):
        names = list(self.__names(s, DAILY_STEPS, REST_HR))
        yield from summary_columns(s, f, date, schedule, names)

    def __names(self, s, *names):
        for name in names:
            sname = s.query(StatisticName). \
                filter(StatisticName.name == name,
                       StatisticName.owner == MonitorCalculator).one_or_none()
            if sname:
                yield sname
