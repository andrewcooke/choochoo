
from urwid import Text, WEIGHT, Columns

from ch2.squeal.tables.statistic import StatisticJournal
from ch2.stoats.calculate.summary import SummaryStatistics
from ch2.uweird.fields import PAGE_WIDTH
from . import Field
from ...lib.utils import label, em


class SummaryField(Field):

    def __init__(self, log, journal, summary=None, width=1):
        if summary is None:
            raise Exception('Summary without summary')
        self._summary = summary
        super().__init__(log, journal, width=width)


class GenericField(SummaryField):

    def __init__(self, log, journal, summary=None, width=1):
        if summary is None:
            raise Exception('Summary without summary')
        self._summary = summary
        super().__init__(log, journal, summary=summary, width=width)

    def _format_value(self, value):
        return self._journal.formatted()

    def _widget(self):
        from urwid import Text
        return Text([label('%s: ' % self._summary), em(self._journal.formatted()), ' '])


def summary_columns(log, s, f, date, schedule, names):

    def fill(columns, width):
        while width < PAGE_WIDTH:
            columns.append(Text(''))
            width += 1

    def field_columns(name):
        journals = StatisticJournal.at_interval(s, date, schedule,
                                                SummaryStatistics, name,
                                                SummaryStatistics)
        columns, width = [], 0
        for named, journal in enumerate(journals):
            summary, period, name = SummaryStatistics.parse_name(journal.statistic_name.name)
            if not named:
                columns.append(Text([name]))
                width += 1
            display = GenericField(log, journal, summary=summary)
            columns.append((WEIGHT, display.width, f(display.widget())))
            width += display.width
        return columns, width

    columns, width = [], 0
    for name in names:
        next_columns, next_width = field_columns(name)
        if width + next_width > PAGE_WIDTH:
            fill(columns, width)
            yield Columns(columns)
            columns, width = [], 0
        columns += next_columns
        width += next_width

    if columns:
        fill(columns, width)
        yield Columns(columns)