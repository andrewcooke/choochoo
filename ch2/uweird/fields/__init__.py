
from abc import ABC, abstractmethod

from urwid import Text, Columns, WEIGHT

from ...squeal.tables.statistic import StatisticJournal, StatisticJournalType
from ...stoats.calculate.summary import SummaryStatistics

PAGE_WIDTH = 4


class Field(ABC):

    def __init__(self, log, journal, width=1):
        self._log = log
        self._journal = journal
        self.width = width

    def __str__(self):
        if self._journal.value is None:
            return '%s: _' % self._journal.statistic_name.name + self._format_units()
        else:
            return '%s: ' % self._journal.statistic_name.name + \
                   self._format_value(self._journal.value) + self._format_units()

    @abstractmethod
    def _format_value(self, value):
        pass

    def _format_units(self):
        return (' ' + self._journal.statistic_name.units) if self._journal.statistic_name.units else ''

    def widget(self):
        return self._widget()

    @abstractmethod
    def _widget(self):
        pass


def summary_columns(log, s, f, date, schedule, names, fields=None):
    from .summary import Float, SUMMARY_FIELDS
    columns = []
    if not fields:
        fields = [None] * len(names)
    fields_and_names = zip(fields, names)
    for field, name in fields_and_names:
        journals = StatisticJournal.at_interval(s, date, schedule,
                                                # id of source field is constraint for summary
                                                SummaryStatistics, name.id,
                                                SummaryStatistics)
        if columns and len(journals) + 1 + len(columns) > PAGE_WIDTH:
            while len(columns) < PAGE_WIDTH:
                columns.append(Text(''))
            yield Columns(columns)
            columns = []
        for named, journal in enumerate(journals):
            summary, period, name = SummaryStatistics.parse_name(journal.statistic_name.name)
            if not named:
                columns.append(Text([name]))
            if field and journal.type == field.type and field.type == StatisticJournalType.FLOAT:
                display = Float(log, journal, *field.display_args,
                                summary=summary, **field.display_kargs)
            else:
                display = SUMMARY_FIELDS[journal.type](log, journal, summary=summary)
            columns.append((WEIGHT, 1, f(display.widget())))
            if len(columns) == PAGE_WIDTH:
                yield Columns(columns)
                columns = []
    if columns:
        while len(columns) < PAGE_WIDTH:
            columns.append(Text(''))
        yield Columns(columns)
