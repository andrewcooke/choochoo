
from urwid import Text

from . import Field, PAGE_WIDTH
from ..lib.utils import label
from ..squeal.tables.statistic import StatisticJournalType


class FloatSummary(Field):

    def __init__(self, log, journal, lo=None, hi=None, dp=2, format='%f', width=1):
        super().__init__(log, journal, width=width)
        self._lo = lo
        self._hi = hi
        self._dp = dp
        self._format = format

    def _format_value(self, value):
        return self._format % value

    def _widget(self, journal):
        format = '%%.%df ' % self._dp
        return Text([label('%s: ' % journal.statistic_name.name),
                     format % journal.value,
                     label(journal.statistic_name.units if journal.statistic_name.units else '')])


class TextSummary(Field):

    def __init__(self, log, journal, width=PAGE_WIDTH):
        super().__init__(log, journal, width=width)

    def _format_value(self, value):
        return repr(value)

    def _widget(self, journal):
        return Text([label('%s: ' % journal.statistic_name.name), journal.value or ''])


class IntegerSummary(Field):

    def __init__(self, log, journal, width=PAGE_WIDTH):
        super().__init__(log, journal, width=width)

    def _format_value(self, value):
        return str(value)

    def _widget(self, journal):
        return Text([label('%s: ' % journal.statistic_name.name),
                     '%d ' % journal.value,
                     label(journal.statistic_name.units if journal.statistic_name.units else '')])


SUMMARY_FIELDS = {StatisticJournalType.TEXT: TextSummary,
                  StatisticJournalType.INTEGER: IntegerSummary,
                  StatisticJournalType.FLOAT: FloatSummary}



