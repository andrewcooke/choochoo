
from urwid import Text

from . import Field
from ...lib.utils import label, em
from ...squeal.tables.statistic import StatisticJournalType


class SummaryField(Field):

    def __init__(self, log, journal, summary=None, width=1):
        if summary is None:
            raise Exception('Summary without summary')
        self._summary = summary
        super().__init__(log, journal, width=width)


class Float(SummaryField):

    def __init__(self, log, journal, lo=None, hi=None, dp=2, format='%f', summary=None, width=1):
        super().__init__(log, journal, summary=summary, width=width)
        self._lo = lo
        self._hi = hi
        self._dp = dp
        self._format = format

    def _format_value(self, value):
        return self._format % value

    def _widget(self):
        from urwid import Text
        format = '%%.%df ' % self._dp
        return Text([label('%s: ' % self._summary),
                     em(format % self._journal.value),
                     label(self._journal.statistic_name.units if self._journal.statistic_name.units else '')])


class Text(SummaryField):

    def _format_value(self, value):
        return repr(value)

    def _widget(self):
        from urwid import Text
        return Text([label('%s: ' % self._summary), em(self._journal.value or '')])


class Integer(SummaryField):

    def _format_value(self, value):
        return str(value)

    def _widget(self):
        from urwid import Text
        return Text([label('%s: ' % self._summary),
                     em('%d ' % self._journal.value),
                     label(self._journal.statistic_name.units if self._journal.statistic_name.units else '')])


SUMMARY_FIELDS = {StatisticJournalType.TEXT: Text,
                  StatisticJournalType.INTEGER: Integer,
                  StatisticJournalType.FLOAT: Float}



