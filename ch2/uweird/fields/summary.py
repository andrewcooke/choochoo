
from urwid import Text, WEIGHT, Columns

from . import Field, PAGE_WIDTH
from ...lib.utils import label, em
from ...squeal.tables.statistic import StatisticJournal
from ...stoats.calculate.summary import SummaryCalculator


class SummaryField(Field):

    def __init__(self, log, journal, summary=None, width=1):
        if summary is None:
            raise Exception('Summary without summary')
        self._summary = summary
        super().__init__(log, journal, width=width)

    def _format_value(self, value):
        return self._journal.formatted()

    def _widget(self):
        from urwid import Text
        return Text([label('%s: ' % self._summary), em(self._journal.formatted()), ' '])


def summary_columns(log, s, f, date, schedule, names, format_name=lambda n: n):

    def fill(columns, width):
        while width < PAGE_WIDTH:
            columns.append(Text(''))
            width += 1

    def field_columns(name):
        journals = StatisticJournal.at_interval(s, date, schedule, SummaryCalculator, name, SummaryCalculator)
        for named, journal in enumerate(journals):
            summary, period, name = SummaryCalculator.parse_name(journal.statistic_name.name)
            if not named:
                yield Text([format_name(name)]), 1
            display = SummaryField(log, journal, summary=summary)
            yield (WEIGHT, display.width, f(display.widget())), display.width,

    # layout algo here tweaked for subjective appearance
    columns, width = [], 0
    for name in names:
        if width % 2 and width < PAGE_WIDTH:
            columns.append(Text(''))
            width += 1
        lookahead = sum(x[1] for x in field_columns(name))
        if width and width + lookahead > PAGE_WIDTH:
            fill(columns, width)
            yield Columns(columns)
            columns, width = [], 0
        for next_column, next_width in field_columns(name):
            if width + next_width > PAGE_WIDTH:
                fill(columns, width)
                yield Columns(columns)
                columns, width = [], 0
            columns.append(next_column)
            width += next_width

    if columns:
        fill(columns, width)
        yield Columns(columns)
