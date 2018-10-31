
from urwid import Text, Columns, Pile

from . import Displayer
from ..calculate.monitor import MonitorStatistics
from ..names import STEPS, REST_HR
from ...lib.date import to_date
from ...lib.utils import label
from ...squeal.tables.statistic import StatisticJournal
from ...uweird.tui.decorators import Indent


class MonitorDiary(Displayer):

    def build(self, s, f, date, schedule=None):
        date = to_date(date)
        if schedule:
            yield from self.__build_schedule(s, date, schedule)
        else:
            yield from self.__build_date(s, date)

    def __build_date(self, s, date):
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
        sjournal = StatisticJournal.at_date(s, date, name, MonitorStatistics, None)
        if sjournal:
            return Text([label(name + ': '), sjournal.formatted()])
        else:
            return None

    def __build_schedule(self, s, date, schedule):
        journals = self.__field_schedule(s, date, schedule, STEPS)
        yield Text('TODO (%d journals)' % len(journals))

    def __field_schedule(self, s, date, schedule, name):
        # todo find id from name and use as constraint
        return StatisticJournal.at_interval(s, date, schedule, MonitorStatistics, None, MonitorStatistics)
