
import datetime as dt
from calendar import month_name, day_abbr, Calendar, monthrange

from urwid import Columns, GridFlow, Pile, WidgetWrap, Text, Padding, emit_signal, connect_signal

from .focus import FocusFor, FocusAttr
from .state import ImmutableStatefulText, MutableStatefulText
from .fixed import Fixed


MONTHS = month_name
DAYS2 = list(map(lambda d: day_abbr[d][:2], Calendar(0).iterweekdays()))
DAYS3 = list(map(lambda d: day_abbr[d][:3], Calendar(0).iterweekdays()))


class DateKeyPressMixin:
    """
    Assumes self.state is a date.

    default should be 'd', 'w', 'm' or 'y'
    delta should be +1 or -1
    """

    def __init__(self, default, delta=1):
        self.__default = default
        self.__delta = delta

    def keypress(self, size, key):
        if self._command_map[key] == 'activate':
            key = self.__default
        if len(key) == 1:
            if key == '=':
                self.state = dt.date.today()
                return
            delta = self.__delta
            if key in '+- ':
                key = 'd' if self.__default == '=' else self.__default
                if key == '-': delta *= -1
            if '0' <= key <= '9':
                delta *= 10 if key == '0' else int(key)
                key = 'd' if self.__default == '=' else self.__default
            if key in 'DWMY':
                key = key.lower()
                delta *= -1
            if key == 'w':
                key = 'd'
                delta *= 7
            if key == 'y':
                key = 'm'
                delta *= 12
            if key == 'd':
                self.state = self.state + dt.timedelta(days=delta)
                return
            elif key == 'm':
                year, month, day = self.state.year, self.state.month, self.state.day
                month += delta
                while month < 1:
                    year -= 1
                    month += 12
                while month > 12:
                    year += 1
                    month -= 12
                day = min(day, monthrange(year, month)[1])
                self.state = dt.date(year, month, day)
                return
        return key


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


class Month(DateKeyPressMixin, MutableStatefulText):

    def __init__(self, date):
        MutableStatefulText.__init__(self, date)
        DateKeyPressMixin.__init__(self, 'm')

    def state_as_text(self):
        return MONTHS[self.state.month]


class Year(DateKeyPressMixin, MutableStatefulText):

    def __init__(self, date):
        MutableStatefulText.__init__(self, date)
        DateKeyPressMixin.__init__(self, 'y')

    def state_as_text(self):
        return str(self.state.year)


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
        # so instead put names in pile
        names = GridFlow(list(map(lambda d: Text(('plain', d)), DAYS2)), 2, 1, 0, 'left')
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
            connect_signal(day._original_widget, 'click', calendar.date_change)
        dates = GridFlow(dates, 2, 1, 0, 'left')
        return Pile([names, dates])


class StatefulSymbol(MutableStatefulText):

    signals = ['click']

    def __init__(self, state, symbol):
        self._symbol = symbol
        # call super after saving symbol so we can display it
        super().__init__(state)

    def state_as_text(self):
        return self._symbol

    def mouse_event(self, size, event, button, col, row, focus):
        if event == 'mouse release' and focus:
            self.keypress(size, ' ')
            return True
        else:
            return False


class QuickChange(DateKeyPressMixin, StatefulSymbol):

    def __init__(self, date, symbol, sign):
        StatefulSymbol.__init__(self, date, symbol)
        DateKeyPressMixin.__init__(self, 'd', sign)


class Today(DateKeyPressMixin, StatefulSymbol):

    def __init__(self, date, symbol):
        StatefulSymbol.__init__(self, date, symbol)
        DateKeyPressMixin.__init__(self, '=')


class BaseDate(WidgetWrap):

    signals = ['change', 'postchange']

    def __init__(self, date=None):
        if not date: date = dt.date.today()
        self._date = date
        super().__init__(self._make(date))

    @property
    def date(self):
        return self._date

    def _make(self, date):
        raise NotImplemented()

    def date_change(self, unused_widget, date):
        if date != self._date:
            # again, arg convention matches Edit
            emit_signal(self, 'change', self, date)
            old_date = date
            self._date = date
            focus = FocusFor(self._w)
            self._w = self._make(self._date)
            focus.apply(self._w)
            emit_signal(self, 'postchange', self, old_date)


class Calendar(BaseDate):
    """
    Displays a text calendar with signal when date changed.
    """

    def _make(self, date):
        down = QuickChange(date, '<', -1)
        connect_signal(down, 'change', self.date_change)
        today = Today(date, '=')
        connect_signal(today, 'change', self.date_change)
        up = QuickChange(date, '>', 1)
        connect_signal(up, 'change', self.date_change)
        month = Month(date)
        connect_signal(month, 'change', self.date_change)
        year = Year(date)
        connect_signal(year, 'change', self.date_change)
        title = Columns([(1, FocusAttr(down)),
                         (1, FocusAttr(today)),
                         (1, FocusAttr(up)),
                         ('weight', 1, Padding(FocusAttr(month), align='center', width='pack')),
                         (4, FocusAttr(year))])
        return Fixed(Pile([title, Days(date, self)]), 20)


class DayOfMonth(DateKeyPressMixin, MutableStatefulText):

    def __init__(self, state):
        MutableStatefulText.__init__(self, state)
        DateKeyPressMixin.__init__(self, 'd')

    def state_as_text(self):
        return str(self.state.day)


class DayOfWeek(DateKeyPressMixin, MutableStatefulText):

    def __init__(self, state):
        MutableStatefulText.__init__(self, state)
        DateKeyPressMixin.__init__(self, 'd')

    def state_as_text(self):
        return DAYS3[self.state.weekday()]


class TextDate(BaseDate):

    def _make(self, date):
        down = QuickChange(date, '<', -1)
        connect_signal(down, 'change', self.date_change)
        today = Today(date, '=')
        connect_signal(today, 'click', self.date_change)
        up = QuickChange(date, '>', 1)
        connect_signal(up, 'change', self.date_change)
        year = Year(date)
        connect_signal(year, 'change', self.date_change)
        month = Month(date)
        connect_signal(month, 'change', self.date_change)
        day_of_month = DayOfMonth(date)
        connect_signal(day_of_month, 'change', self.date_change)
        day_of_week = DayOfWeek(date)
        connect_signal(day_of_week, 'change', self.date_change)
        return Columns([(1, FocusAttr(down)),
                        (1, FocusAttr(today)),
                        (1, FocusAttr(up)),
                        ('weight', 1, Padding(FocusAttr(year), align='center', width='pack')),
                        ('weight', 1, Padding(FocusAttr(month), align='center', width='pack')),
                        ('weight', 1, Padding(FocusAttr(day_of_month), align='center', width='pack')),
                        ('weight', 1, Padding(FocusAttr(day_of_week), align='center', width='pack'))])
