
from logging import getLogger

from urwid import Text, Columns, Pile

from . import Displayer
from ..calculate.monitor import MonitorCalculator
from ..names import REST_HR, DAILY_STEPS
from ...squeal.tables.statistic import StatisticJournal, StatisticName
from ...uweird.fields import ReadOnlyField
from ...uweird.fields.summary import summary_columns
from ...uweird.tui.decorators import Indent

log = getLogger(__name__)


class MonitorDiary(Displayer):

    def _display_date(self, s, f, date):
        columns = self.__fields(s, date)
        if columns:
            yield Pile([Text('Monitor'),
                        Indent(Columns(columns))])

    def __fields(self, s, date):
        steps = self.__field(s, date, DAILY_STEPS)
        rest_hr = self.__field(s, date, REST_HR)
        if steps or rest_hr:
            return [steps if steps else Text(''), rest_hr if rest_hr else Text('')]
        else:
            return None

    def __field(self, s, date, name):
        sjournal = StatisticJournal.at_date(s, date, name, MonitorCalculator, None)
        if sjournal:
            return ReadOnlyField(log, sjournal, date=date).widget()
        else:
            return None

    def _display_schedule(self, s, f, date, schedule=None):
        columns = list(self.__schedule_fields(s, f, date, schedule))
        if columns:
            yield Pile([Text('Monitor'),
                        Indent(Pile(columns))])

    def __schedule_fields(self, s, f, date, schedule):
        names = list(self.__names(s, DAILY_STEPS, REST_HR))
        yield from summary_columns(log, s, f, date, schedule, names)

    def __names(self, s, *names):
        for name in names:
            sname = s.query(StatisticName). \
                filter(StatisticName.name == name,
                       StatisticName.owner == MonitorCalculator).one_or_none()
            if sname:
                yield sname
