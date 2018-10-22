
from urwid import Text, Columns, Pile

from ch2.uweird.tui.decorators import Indent
from ..calculate.monitor import MonitorStatistics
from ..names import STEPS, \
    REST_HR
from ...lib.date import to_date
from ...lib.utils import label
from ...squeal.tables.statistic import StatisticJournal


class MonitorDiary:

    def __init__(self, log):
        self._log = log

    def build(self, s, f, date):
        date = to_date(date)
        columns = self.__fields(s, date)
        if columns:
            yield Pile([Text('Monitor'),
                        Indent(Columns(columns))])

    def __fields(self, s, date):
        steps = self.__field(s, date, STEPS)
        rest_hr = self.__field(s, date, REST_HR)
        if steps or rest_hr:
            return [steps if steps else Text(''), rest_hr if rest_hr else Text('')]
        else:
            return None

    def __field(self, s, date, name):
        sjournal = StatisticJournal.get(s, name, date, MonitorStatistics, None)
        if sjournal:
            return Text([label(name + ': '), sjournal.formatted()])
        else:
            return None
