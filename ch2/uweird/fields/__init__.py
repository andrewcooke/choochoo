from abc import ABC, abstractmethod

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