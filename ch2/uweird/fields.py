
from abc import abstractmethod, ABC

from urwid import Edit, connect_signal

from ..lib.utils import label
from ..squeal.tables.statistic import StatisticJournalType
from ..uweird.tui.widgets import Rating0, Rating1

PAGE_WIDTH = 4


class Base(ABC):

    def __init__(self, log, s, journal, width=1):
        self._log = log
        self.__session = s
        self.__journal = journal
        self.width = width

    def __str__(self):
        if self.__journal.value is None:
            return '%s: _' % self.__journal.statistic_name.name + self._format_units()
        else:
            return '%s: ' % self.__journal.statistic_name.name + \
                   self._format_value(self.__journal.value) + self._format_units()

    @abstractmethod
    def _format_value(self, value):
        pass

    def _format_units(self):
        return (' ' + self.__journal.statistic_name.units) if self.__journal.statistic_name.units else ''

    def bound_widget(self):
        widget = self._widget(self.__journal)
        connect_signal(widget, 'change', self.__on_change)
        return widget

    def __on_change(self, widget, value):
        self._log.debug('Setting %s=%r' % (self.__journal.statistic_name.name, value))
        self.__journal.value = value

    @abstractmethod
    def _widget(self, journal):
        pass


class Text(Base):

    statistic_journal_type = StatisticJournalType.TEXT

    def __init__(self, log, s, journal, width=PAGE_WIDTH):
        super().__init__(log, s, journal, width=width)

    def _format_value(self, value):
        return repr(value)

    def _widget(self, journal):
        return Edit(caption=label('%s: ' % journal.statistic_name.name), edit_text=journal.value or '')


class Integer(Base):

    statistic_journal_type = StatisticJournalType.INTEGER

    def __init__(self, log, s, journal, lo=None, hi=None, width=1):
        super().__init__(log, s, journal, width=width)
        self._lo = lo
        self._hi = hi

    def _format_value(self, value):
        return '%d' % value

    def _widget(self, journal):
        from .tui.widgets import Integer
        return Integer(caption=label('%s: ' % journal.statistic_name.name), state=journal.value,
                       minimum=self._lo, maximum=self._hi, units=journal.statistic_name.units)


class Float(Base):

    statistic_journal_type = StatisticJournalType.FLOAT

    def __init__(self, log, s, journal, lo=None, hi=None, dp=2, format='%f', width=1):
        super().__init__(log, s, journal, width=width)
        self._lo = lo
        self._hi = hi
        self._dp = dp
        self._format = format

    def _format_value(self, value):
        return self._format % value

    def _widget(self, journal):
        from .tui.widgets import Float
        return Float(caption=label('%s: ' % journal.statistic_name.name), state=journal.value,
                     minimum=self._lo, maximum=self._hi, dp=self._dp, units=journal.statistic_name.units)


class Score(Base):

    statistic_journal_type = StatisticJournalType.INTEGER

    def __init__(self, log, s, journal, width=1):
        super().__init__(log, s, journal, width=width)

    def _format_value(self, value):
        return '%d' % value

    def _widget(self, journal):
        return self._field_cls(caption=label('%s: ' % journal.statistic_name.name), state=journal.value)

    @property
    @abstractmethod
    def _field_cls(self):
        pass


class Score0(Score):

    _field_cls = Rating0


class Score1(Score):

    _field_cls = Rating1
