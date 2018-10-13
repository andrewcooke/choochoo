
from abc import abstractmethod, ABC

from urwid import Edit, connect_signal

from ..uweird.tui.widgets import Rating
from ..squeal.tables.statistic import StatisticType

PAGE_WIDTH = 4


class Base(ABC):

    def __init__(self, log, s, journal, width=1):
        self._log = log
        self.__session = s
        self.__journal = journal
        self.width = width

    def __str__(self):
        if self.__journal.value is None:
            return '%s: _' % self.__journal.statistic.name + self._format_units()
        else:
            return '%s: ' % self.__journal.statistic.name + \
                   self._format_value(self.__journal.value) + self._format_units()

    @abstractmethod
    def _format_value(self, value):
        pass

    def _format_units(self):
        return (' ' + self.__journal.statistic.units) if self.__journal.statistic.units else ''

    def bound_widget(self):
        widget = self._widget(self.__journal)
        connect_signal(widget, 'change', self.__on_change)
        return widget

    def __on_change(self, widget, value):
        self._log.debug('Setting %s=%r' % (self.__journal.statistic.name, value))
        self.__journal.value = value

    @abstractmethod
    def _widget(self, journal):
        pass


class Text(Base):

    statistic_type = StatisticType.TEXT

    def __init__(self, log, s, journal, width=PAGE_WIDTH):
        super().__init__(log, s, journal, width=width)

    def _format_value(self, value):
        return repr(value)

    def _widget(self, journal):
        return Edit(caption='%s: ' % journal.statistic.name, edit_text=journal.value or '')


class Integer(Base):

    statistic_type = StatisticType.INTEGER

    def __init__(self, log, s, journal, lo=None, hi=None, width=1):
        super().__init__(log, s, journal, width=width)
        self._lo = lo
        self._hi = hi

    def _format_value(self, value):
        return '%d' % value

    def _widget(self, journal):
        from .tui.widgets import Integer
        return Integer(caption='%s: ' % journal.statistic.name, state=journal.value,
                       minimum=self._lo, maximum=self._hi, units=journal.statistic.units)


class Float(Base):

    statistic_type = StatisticType.FLOAT

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
        return Float(caption='%s: ' % journal.statistic.name, state=journal.value,
                     minimum=self._lo, maximum=self._hi, dp=self._dp, units=journal.statistic.units)


class Score(Base):

    statistic_type = StatisticType.INTEGER

    def __init__(self, log, s, journal, width=1):
        super().__init__(log, s, journal, width=width)

    def _format_value(self, value):
        return '%d' % value

    def _widget(self, journal):
        return Rating(caption='%s: ' % journal.statistic.name, state=journal.value)
