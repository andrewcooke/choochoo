
import datetime as dt
from calendar import month_name, day_abbr, Calendar, monthrange

from urwid import Columns, GridFlow, Pile, WidgetWrap, Text, Padding, emit_signal, connect_signal

from .urweird.focus import FocusFor, FocusAttr
from .urweird.state import ImmutableStatefulText, MutableStatefulText
from .urweird.fixed import Fixed
from .utils import sign


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
        if key in '-+':
            self.state = self.state + (1 if key == '+' else -1)
            return
        return key


class Day(ImmutableStatefulText):

    signals = ['click']

    def state_as_text(self):
        return '%2s' % self.state.day

    def keypress(self, size, key):
        if self._command_map[key] == 'activate':
            emit_signal(self, 'click', self.state)
        else:
            return key

    def mouse_event(self, size, event, button, col, row, focus):
        if event == 'mouse release' and focus:
            emit_signal(self, 'click', self.state)
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
            connect_signal(day._original_widget, 'click', calendar._date_changed)
        dates = GridFlow(dates, 2, 1, 0, 'left')
        return Pile([names, dates])


class QuickChange(MutableStatefulText):

    def __init__(self, date, symbol, sign):
        self._date = date
        self._symbol = symbol
        self._sign = sign
        super().__init__(date)

    def state_as_text(self):
        return self._symbol

    def keypress(self, size, key):
        if key in ' +-':
            self.state = self.state + self._sign * dt.timedelta(days=1) * (-1 if key == '-' else 1)
        elif '0' <= key <= '9':
            self.state = self.state + self._sign * dt.timedelta(days=1) * (10 if key == '0' else int(key))
        elif key == 'm':
            month, year = add_month(self.state.month, self.state.year, self._sign)
            day = min(self.state.day, monthrange(year, month)[1])
            self.state = dt.date(year, month, day)
        elif key == 'y':
            year = self.state.year + 1
            day = min(self.state.day, monthrange(year, self.state.month)[1])
            self.state = dt.date(year, self.state.month, day)
        else:
            return key


class Calendar(WidgetWrap):
    """
    Displays a text calendar with signal when date changed.
    """

    signals = ['change', 'postchange']

    def __init__(self, date=None):
        if not date: date = dt.date.today()
        self._date = date
        super().__init__(self._make(date))

    def _make(self, date):
        down = QuickChange(date, '<', -1)
        connect_signal(down, 'change', self._date_changed)
        up = QuickChange(date, '>', 1)
        connect_signal(up, 'change', self._date_changed)
        month = Month((date.month, date.year))
        connect_signal(month, 'change', self._month_year_changed)
        year = Year(date.year)
        connect_signal(year, 'change', self._year_changed)
        title = Columns([(1, FocusAttr(down)),
                         (1, FocusAttr(up)),
                         ('weight', 1, Padding(FocusAttr(month), align='center', width='pack')),
                         (4, FocusAttr(year))])
        return Fixed(Pile([title, Days(date, self)]), 20)

    def _year_changed(self, year):
        self._changed(year=year)

    def _month_year_changed(self, month_year):
        self._changed(month=month_year[0], year=month_year[1])

    def _date_changed(self, date):
        self._changed(day=date.day, month=date.month, year=date.year)

    def _changed(self, day=None, month=None, year=None):
        if day is None: day = self._date.day
        if month is None: month = self._date.month
        if year is None: year = self._date.year
        # if the month is shorter we may need to change days
        day = min(day, monthrange(year, month)[1])
        date = dt.date(year, month, day)
        if date != self._date:
            emit_signal(self, 'change', date)
            old_date = date
            self._date = date
            focus = FocusFor(self._w)
            self._w = self._make(self._date)
            focus.apply(self._w)
            emit_signal(self, 'postchange', old_date)
