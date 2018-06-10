
import datetime as dt
from calendar import month_name, day_abbr, Calendar, monthrange

from urwid import Columns, GridFlow, Pile, WidgetWrap, Text, Padding

from .urwid import Focus, ImmutableFocusedText, MutableFocusedText, Fixed
from .utils import sign


MONTHS = month_name
DAYS = list(map(lambda d: day_abbr[d][:2], Calendar(0).iterweekdays()))


class Month(MutableFocusedText):

    def __init__(self, month_year, callback, plain=None, focus=None):
        super().__init__(month_year, callback, plain=plain, focus=focus)

    def keypress(self, size, key):
        month, year = self.state
        if 'a' <= key <= 'z':
            tries = 0
            while tries < 12:
                tries += 1
                month = month % 12 + 1
                if MONTHS[month].lower().startswith(key):
                    self.state = month, year
                    return
        elif key == '+':
            if month == 12:
                month, year = 1, year + 1
            else:
                month, year = month + 1, year
            self.state = month, year
            return
        elif key == '-':
            if month == 1:
                month, year = 12, year - 1
            else:
                month, year = month - 1, year
            self.state = month, year
            return
        return key

    def state_as_text(self):
        return MONTHS[self.state[0]]


class Year(MutableFocusedText):

    def __init__(self, year, callback, plain=None, focus=None):
        super().__init__(year, callback, plain=plain, focus=focus)

    def keypress(self, size, key):
        if '0' <= key <= '9':
            delta = int(key) - self.state % 10
            if abs(delta) > 5:
                delta -= sign(delta) * 10
            self.state = self.state + delta
            return
        if key in '-+':
            self.state = self.state + (1 if key == '+' else -1)
            return
        return key


class Day(ImmutableFocusedText):

    def __init__(self, date, callback, plain=None, focus=None):
        super().__init__(date, plain=plain, focus=focus)
        self._callback = callback

    def state_as_text(self):
        return '%2s' % self.state.day

    def keypress(self, size, key):
        if key == ' ':
            self._callback(day=self.state.day, month=self.state.month, year=self.state.year)
        else:
            return key


class Days(WidgetWrap):

    def __init__(self, date, callback):
        super().__init__(self._make(date, callback))
        self._date = date

    def _make(self, date, callback):
        # if we do this as single gridflow then focus doesn't move down into dates
        names = GridFlow(list(map(lambda d: Text(('plain', d)), DAYS)), 2, 1, 0, 'left')
        prev = dt.date(date.year if date.month > 1 else date.year - 1,
                       date.month - 1 if date.month > 1 else 12, 1)
        next = dt.date(date.year if date.month < 12 else date.year + 1,
                       date.month + 1 if date.month < 12 else 1, 1)
        prev_days = monthrange(prev.year, prev.month)[1]
        curr_days = monthrange(date.year, date.month)[1]
        first_day = dt.date(date.year, date.month, 1).weekday()  # mon 0
        total_days = first_day + curr_days
        extra_days = 7 - total_days % 7
        if extra_days == 7:
            extra_days = 0
        else:
            total_days += extra_days
        dates = [Day(dt.date(prev.year, prev.month, i), callback, 'unimportant')
                 for i in range(prev_days - first_day + 1, prev_days + 1)]
        dates.extend([Day(dt.date(date.year, date.month, i), callback)
                      for i in range(1, curr_days + 1)])
        dates.extend([Day(dt.date(next.year, next.month, i), callback, 'unimportant')
                      for i in range(1, extra_days + 1)])
        dates = GridFlow(dates, 2, 1, 0, 'left')
        return Pile([names, dates])


class Calendar(WidgetWrap):
    """
    Displays a text calendar with callback when date changed.
    """

    def __init__(self, date=None, callback=None):
        if not date: date = dt.date.today()
        self._date = date
        self._callback = callback
        super().__init__(self._make(date))

    def _make(self, date):
        title = Columns([Padding(Month((date.month, date.year), lambda my: self._date_changed(month=my[0], year=my[1])),
                                 align='center', width='pack'),
                         Padding(Year(date.year, lambda y: self._date_changed(year=y)),
                                 align='center', width='pack')])
        # spearate title from days to avoid focus problems
        return Fixed(Pile([title, Days(date, self._date_changed)]), 20)

    def _date_changed(self, day=None, month=None, year=None):
        if day is None: day = self._date.day
        if month is None: month = self._date.month
        if year is None: year = self._date.year
        self._date = dt.date(year, month, day)
        focus = Focus(self._w)
        self._w = self._make(self._date)
        focus.apply(self._w)
        if self._callback: self._callback(self._date)
