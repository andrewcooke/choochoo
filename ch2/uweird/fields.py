from abc import abstractmethod

PAGE_WIDTH = 3


class Base:

    def __init__(self, log, s, journal, width=1):
        self._log = log
        self._session = s
        self._journal = journal
        self.width = width

    def __str__(self):
        if self._journal.value is None:
            return '%s: _' % self._journal.statistic.name + self._format_units()
        else:
            return ('%s: ' % self._journal.statistic.name) + self._format_value() + self._format_units()

    @abstractmethod
    def _format_value(self):
        pass

    def _format_units(self):
        return (' ' + self._journal.statistic.units) if self._journal.statistic.units else ''

    def bound_widget(self):
        widget = self._widget()
        # bind
        return widget

    @abstractmethod
    def _widget(self):
        pass


class Text(Base):

    def __init__(self, log, s, journal, width=PAGE_WIDTH):
        super().__init__(log, s, journal, width=width)

    def _format_value(self):
        return repr(self._journal.value)


class Integer(Base):

    def __init__(self, log, s, journal, lo=None, hi=None, width=1):
        super().__init__(log, s, journal, width=width)
        self._lo = lo
        self._hi = hi

    def _format_value(self):
        return '%d' % self._journal.value


class Float(Base):

    def __init__(self, log, s, journal, lo=None, hi=None, format='%f', width=1):
        super().__init__(log, s, journal, width=width)
        self._lo = lo
        self._hi = hi
        self._format = format

    def _format_value(self):
        return self._format % self._journal.value


class Score(Base):

    def __init__(self, log, s, journal, width=1):
        super().__init__(log, s, journal, width=width)

    def _format_value(self):
        return '%d' % self._journal.value
