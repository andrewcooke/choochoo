
import datetime as dt
from calendar import month_name, day_abbr, Calendar, monthrange

from urwid import Columns, GridFlow, Pile, WidgetWrap, Text, Padding, emit_signal, connect_signal

from .focus import FocusFor, FocusAttr
from .state import ImmutableStatefulText, MutableStatefulText
from .fixed import Fixed
from ..utils import sign


MONTHS = month_name
DAYS = list(map(lambda d: day_abbr[d][:2], Calendar(0).iterweekdays()))


def add_month(month, year, sign):
    if sign > 0:
        if month == 12:
            month, year = 1, year + 1
        else:
            month, year = month + 1, year
    else:
        if month == 1:
            month, year = 12, year - 1
        else:
            month, year = month - 1, year
    return month, year


def clip_day(day, month, year):
    return min(day, monthrange(year, month)[1])


class Month(MutableStatefulText):

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
        elif key in '+-':
            month, year = add_month(month, year, 1 if key == '+' else -1)
            self.state = month, year
            return
        else:
            return key

    def state_as_text(self):
        return MONTHS[self.state[0]]


class Year(MutableStatefulText):

    def keypress(self, size, key):
        if '0' <= key <= '9':
            delta = int(key) - self.state % 10
            if abs(delta) > 5:
                delta -= sign(delta) * 10
            self.state = self.state + delta
            return
        elif key in '-+':
            self.state = self.state + (1 if key == '+' else -1)
            return
        else:
            return key


class Day(ImmutableStatefulText):

    signals = ['click']

    def state_as_text(self):
        return '%2s' % self.state.day

    def keypress(self, size, key):
        if self._command_map[key] == 'activate':
            emit_signal(self, 'click', self, self.state)
        else:
            return key

    def mouse_event(self, size, event, button, col, row, focus):
        if event == 'mouse release' and focus:
            emit_signal(self, 'click', self, self.state)
            return True
        else:
            return False


class Days(WidgetWrap):

    def __init__(self, date, calendar):
        super().__init__(self._make(date, calendar))
        self._date = date

    def _make(self, date, calendar):
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
        dates = [FocusAttr(Day(dt.date(prev.year, prev.month, i)), 'unimportant')
                 for i in range(prev_days - first_day + 1, prev_days + 1)]
        dates.extend([FocusAttr(Day(dt.date(date.year, date.month, i)),
                                plain='selected' if i == date.day else 'plain',
                                focus='selected-focus' if i == date.day else 'plain-focus')
                      for i in range(1, curr_days + 1)])
        dates.extend([FocusAttr(Day(dt.date(next.year, next.month, i)), 'unimportant')
                      for i in range(1, extra_days + 1)])
        for day in dates:
            connect_signal(day._original_widget, 'click', calendar._date_change)
        dates = GridFlow(dates, 2, 1, 0, 'left')
        return Pile([names, dates])


class StatefulSymbol(MutableStatefulText):

    def __init__(self, state, symbol):
        self._symbol = symbol
        # call super after saving symbol so we can display it
        super().__init__(state)

    def state_as_text(self):
        return self._symbol


class QuickChange(StatefulSymbol):
    """
    < or > at the top left of the calendar - change by a day, or number of days, or
    a week, month, or year.
    """

    def __init__(self, date, symbol, sign):
        super().__init__(date, symbol)
        self._sign = sign

    def keypress(self, size, key):
        if key in ' +-':
            self.state = self.state + self._sign * dt.timedelta(days=1) * (-1 if key == '-' else 1)
        elif '0' <= key <= '9':
            self.state = self.state + self._sign * dt.timedelta(days=1) * (10 if key == '0' else int(key))
        elif key == 'w':
            self.state = self.state + self._sign * dt.timedelta(days=1) * 7
        elif key == 'm':
            month, year = add_month(self.state.month, self.state.year, self._sign)
            day = clip_day(self.state.day, month, year)
            self.state = dt.date(year, month, day)
        elif key == 'y':
            year = self.state.year + self._sign
            day = clip_day(self.state.day, self.state.month, year)
            self.state = dt.date(year, self.state.month, day)
        elif key == '=':
            self.state = dt.date.today()
        else:
            return key


class Today(StatefulSymbol):
    """
    Shortcut for today's date,
    """

    signals = ['click']

    def __init__(self, symbol):
        # actually a hack because we have no state
        super().__init__(None, symbol)

    def keypress(self, size, key):
        if self._command_map[key] == 'activate':
            emit_signal(self, 'click', self, dt.date.today())
        else:
            return key

    def mouse_event(self, size, event, button, col, row, focus):
        if event == 'mouse release' and focus:
            emit_signal(self, 'click', self, dt.date.today())
            return True
        else:
            return False


class Calendar(WidgetWrap):
    """
    Displays a text calendar with signal when date changed.
    """

    signals = ['change', 'postchange']

    def __init__(self, date=None):
        if not date: date = dt.date.today()
        self._date = date
        super().__init__(self._make(date))

    @property
    def date(self):
        return self._date

    def _make(self, date):
        down = QuickChange(date, '<', -1)
        connect_signal(down, 'change', self._date_change)
        today = Today('=')
        connect_signal(today, 'click', self._date_change)
        up = QuickChange(date, '>', 1)
        connect_signal(up, 'change', self._date_change)
        month = Month((date.month, date.year))
        connect_signal(month, 'change', self._month_year_change)
        year = Year(date.year)
        connect_signal(year, 'change', self._year_change)
        title = Columns([(1, FocusAttr(down)),
                         (1, FocusAttr(today)),
                         (1, FocusAttr(up)),
                         ('weight', 1, Padding(FocusAttr(month), align='center', width='pack')),
                         (4, FocusAttr(year))])
        return Fixed(Pile([title, Days(date, self)]), 20)

    def _year_change(self, unused_widget, year):
        self._change(year=year)

    def _month_year_change(self, unused_widget, month_year):
        self._change(month=month_year[0], year=month_year[1])

    def _date_change(self, unused_widget, date):
        self._change(day=date.day, month=date.month, year=date.year)

    def _change(self, day=None, month=None, year=None):
        if day is None: day = self._date.day
        if month is None: month = self._date.month
        if year is None: year = self._date.year
        # if the month is shorter we may need to change days
        day = clip_day(day, month, year)
        date = dt.date(year, month, day)
        if date != self._date:
            # again, arg convention matches Edit
            emit_signal(self, 'change', self, date)
            old_date = date
            self._date = date
            focus = FocusFor(self._w)
            self._w = self._make(self._date)
            focus.apply(self._w)
            emit_signal(self, 'postchange', self, old_date)
