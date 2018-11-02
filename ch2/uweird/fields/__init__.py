
from abc import ABC, abstractmethod

from urwid import Text

from ...lib.utils import label, em

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


class ReadOnlyField(Field):

    def __init__(self, log, journal, width=1, date=None):
        self._date = date
        super().__init__(log, journal, width=width)

    def _format_value(self, value):
        return self._journal.formatted()

    def _widget(self):
        if self._date:
            measures = self._journal.measures_as_text(self._date)
        else:
            measures = []
        if measures:
            self.width += 1
        return Text([label('%s: ' % self._journal.statistic_name.name), em(self._journal.formatted()), ' ']
                    + measures)



