
from . import Field
from ...lib.utils import label, em
from ...squeal.tables.statistic import StatisticJournalType


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
        value = self._journal.formatted()
        return Text([label('%s: ' % self._summary), em(value)])
