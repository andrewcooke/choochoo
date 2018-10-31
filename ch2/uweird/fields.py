
from abc import abstractmethod

from urwid import Edit, connect_signal

from . import Field, PAGE_WIDTH
from ..lib.utils import label
from ..squeal.tables.statistic import StatisticJournalType
from ..uweird.tui.widgets import Rating0, Rating1


class EditableField(Field):

    def widget(self):
        widget = self._widget(self._journal)
        connect_signal(widget, 'change', self.__on_change)
        return widget

    def __on_change(self, widget, value):
        self._log.debug('Setting %s=%r' % (self._journal.statistic_name.name, value))
        self._journal.value = value


class Text(EditableField):

    statistic_journal_type = StatisticJournalType.TEXT

    def __init__(self, log, journal, width=PAGE_WIDTH):
        super().__init__(log, journal, width=width)

    def _format_value(self, value):
        return repr(value)

    def _widget(self, journal):
        return Edit(caption=label('%s: ' % journal.statistic_name.name), edit_text=journal.value or '')


class Integer(Field):

    statistic_journal_type = StatisticJournalType.INTEGER

    def __init__(self, log, journal, lo=None, hi=None, width=1):
        super().__init__(log, journal, width=width)
        self._lo = lo
        self._hi = hi

    def _format_value(self, value):
        return '%d' % value

    def _widget(self, journal):
        from .tui.widgets import Integer
        return Integer(caption=label('%s: ' % journal.statistic_name.name), state=journal.value,
                       minimum=self._lo, maximum=self._hi, units=journal.statistic_name.units)


class Float(EditableField):

    statistic_journal_type = StatisticJournalType.FLOAT

    def __init__(self, log, journal, lo=None, hi=None, dp=2, format='%f', width=1):
        super().__init__(log, journal, width=width)
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


class Score(EditableField):

    statistic_journal_type = StatisticJournalType.INTEGER

    def __init__(self, log, journal, width=1):
        super().__init__(log, journal, width=width)

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
