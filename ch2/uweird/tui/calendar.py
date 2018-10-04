
import datetime as dt
from calendar import month_name, day_abbr, Calendar, monthrange

from urwid import Columns, GridFlow, Pile, Text, Padding, emit_signal, connect_signal, WEIGHT

from .fixed import Fixed
from .focus import FocusFor, FocusAttr, FocusWrap, OnFocus
from .state import ImmutableStatefulText, MutableStatefulText
from ...lib.date import format_date

MONTHS = month_name
DAYS2 = list(map(lambda d: day_abbr[d][:2], Calendar(0).iterweekdays()))
DAYS3 = list(map(lambda d: day_abbr[d][:3], Calendar(0).iterweekdays()))


def clip_day(day, month, year): return min(day, monthrange(year, month)[1])


class DateKeyPressMixin:
    """
    Assumes self.state is a date.

    default should be 'd', 'w', 'm', 'y', 'D' or 'M' (capitals support alpha selection)
    delta should be +1 or -1
    """

    def __init__(self, default, delta=1):
        self.__is_alpha = default.isupper()
        self.__default = default.lower()
        self.__delta = delta

    def keypress(self, size, key):
        original_key = key
        delta = self.__delta
        if len(key) == 1 and key.isupper():
            key = key.lower()
            delta *= -1
        if self.__is_alpha and 'a' <= key <= 'z':
            return self.__alpha_keypress(delta, key, original_key)
        if self._command_map[key] == 'activate':
            key = self.__default
        if key == '=':
            self.state = dt.date.today()
            return
        if len(key) == 1:
            return self.__delta_keypress(delta, key, original_key)
        return original_key

    def __delta_keypress(self, delta, key, original_key):
        if key in '+- ':
            if key == '-': delta *= -1
            key = 'd' if self.__default == '=' else self.__default
        if '0' <= key <= '9':
            delta *= 10 if key == '0' else int(key)
            key = 'd' if self.__default == '=' else self.__default
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
        return original_key

    def __alpha_keypress(self, delta, key, original_key):
        is_month = self.__default == 'm'
        n = 12 if is_month else 7
        tries, date = 0, self.state
        while tries <= n:
            tries += 1
            if is_month:
                date = self.__add_month(date, delta)
                name = MONTHS[date.month]
            else:
                date += dt.timedelta(days=delta)
                name = DAYS2[date.weekday()]
            if name.lower().startswith(key):
                if is_month:
                    date = dt.date(date.year, date.month, clip_day(self.state.day, date.month, date.year))
                self.state = date
                return
        return original_key

    def __add_month(self, date, delta):
        year, month, day = date.year, date.month + delta, date.day
        while month < 1:
            year -= 1
            month += 12
        while month > 12:
            year += 1
            month -= 12
        day = clip_day(day, month, year)
        return dt.date(year, month, day)


class Month(DateKeyPressMixin, MutableStatefulText):

    def __init__(self, date, as_text=True):
        self._as_text = as_text
        MutableStatefulText.__init__(self, date)
        DateKeyPressMixin.__init__(self, 'M')

    def _state_as_text(self):
        if self._as_text:
            return MONTHS[self.state.month]
        else:
            return '%02d' % self.state.month


class MonthBar(OnFocus):

    def __init__(self, date, as_text=True, bar=None):
        super().__init__(Month(date, as_text=as_text),
                         '+/- to inc/dec; first letter to advance; d/m/y/D/M/Y/= as elsewhere', bar)
        self.widget = self._w


class Year(DateKeyPressMixin, MutableStatefulText):

    def __init__(self, date):
        MutableStatefulText.__init__(self, date)
        DateKeyPressMixin.__init__(self, 'y')

    def _state_as_text(self):
        return str(self.state.year)


class YearBar(OnFocus):

    def __init__(self, date, bar=None):
        super().__init__(Year(date), '+/- to inc/dec; digit to jump to nearest; d/m/y/D/M/Y/= as elsewhere', bar)
        self.widget = self._w


class Day(ImmutableStatefulText):

    signals = ['click']

    def _state_as_text(self):
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


class Days(FocusWrap):

    def __init__(self, date, calendar):
        self._date = date
        super().__init__(self._make(calendar))

    def _make(self, calendar):
        # if we do this as single gridflow then focus doesn't move down into dates
        # so instead put names in pile
        names = GridFlow(list(map(lambda d: Text(('plain', d)), DAYS2)), 2, 1, 0, 'left')
        prev = dt.date(self._date.year if self._date.month > 1 else self._date.year - 1,
                       self._date.month - 1 if self._date.month > 1 else 12, 1)
        next = dt.date(self._date.year if self._date.month < 12 else self._date.year + 1,
                       self._date.month + 1 if self._date.month < 12 else 1, 1)
        prev_days = monthrange(prev.year, prev.month)[1]
        curr_days = monthrange(self._date.year, self._date.month)[1]
        first_day = dt.date(self._date.year, self._date.month, 1).weekday()  # mon 0
        total_days = first_day + curr_days
        extra_days = 7 - total_days % 7
        if extra_days == 7:
            extra_days = 0
        else:
            total_days += extra_days
        dates = [FocusAttr(Day(dt.date(prev.year, prev.month, i)), 'unimportant')
                 for i in range(prev_days - first_day + 1, prev_days + 1)]
        dates.extend([FocusAttr(Day(dt.date(self._date.year, self._date.month, i)),
                                plain='selected' if i == self._date.day else 'plain',
                                focus='selected-focus' if i == self._date.day else 'plain-focus')
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

    def _state_as_text(self):
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


DKMSG = {(-1, 'd'): '+/spc/enter/d to dec day; -/D to inc; m/y to dec month/year; M/Y to inc; = now',
         ( 1, 'd'): '+/spc/enter/d to inc day; -/D to dec; m/y to inc month/year; M/Y to dec; = now',
         (-1, 'm'): '+/spc/enter/m to dec month; -/M to inc; d/y to dec day/year; D/Y to inc; = now',
         ( 1, 'm'): '+/spc/enter/m to inc month; -/M to dec; d/y to inc day/year; D/Y to dec; = now',
         (-1, 'y'): '+/spc/enter/y to dec year; -/Y to inc; d/m to dec day/month; D/M to inc; = now',
         ( 1, 'y'): '+/spc/enter/y to inc year; -/Y to dec; d/m to inc day/month; D/M to dec; = now'}


class QuickChangeBar(OnFocus):

    def __init__(self, date, symbol, sign, bar=None):
        super().__init__(QuickChange(date, symbol, sign), DKMSG[(sign, 'd')], bar)
        self.widget = self._w


class Today(DateKeyPressMixin, StatefulSymbol):

    def __init__(self, date, symbol):
        StatefulSymbol.__init__(self, date, symbol)
        DateKeyPressMixin.__init__(self, '=')


class TodayBar(OnFocus):

    def __init__(self, date, symbol, bar=None):
        super().__init__(Today(date, symbol),
                         '%s/spc/enter now; +/d/m/y to inc day/month/year; -/D/M/Y to dec' % symbol, bar)
        self.widget = self._w


class BaseDate(FocusWrap):

    signals = ['change', 'postchange']

    def __init__(self, log, bar=None, date=None):
        self._log = log
        if not date: date = dt.date.today()
        self._date = date
        self._bar = bar
        super().__init__(self._make())

    def __get_state(self):
        return self._date

    def __set_state(self, date):
        self.date_change(None, date)

    state = property(__get_state, __set_state)

    def _make(self):
        raise NotImplemented()

    def date_change(self, unused_widget, date):
        if date != self._date:
            self._log.info('Date has changed: %s - %s' % (format_date(self._date), format_date(date)))
            old_date = date
            self._date = date
            self._log.debug('Sending change signal for date change')
            # again, arg convention matches Edit
            emit_signal(self, 'change', self, self._date)
            focus = FocusFor(self._w, self._log)
            self._w = self._make()
            focus.to(self._w)
            self._log.debug('Sending change signal for date postchange')
            emit_signal(self, 'postchange', self, old_date)


class Calendar(BaseDate):
    """
    Displays a text calendar with signal when date changed.
    """

    def _make(self):
        down = QuickChangeBar(self._date, '<', -1, bar=self._bar)
        connect_signal(down.widget, 'change', self.date_change)
        today = TodayBar(self._date, '=', bar=self._bar)
        connect_signal(today.widget, 'change', self.date_change)
        up = QuickChangeBar(self._date, '>', 1, bar=self._bar)
        connect_signal(up.widget, 'change', self.date_change)
        month = MonthBar(self._date, bar=self._bar)
        connect_signal(month.widget, 'change', self.date_change)
        year = YearBar(self._date, bar=self._bar)
        connect_signal(year.widget, 'change', self.date_change)
        title = Columns([(1, FocusAttr(down)),
                         (1, FocusAttr(today)),
                         (1, FocusAttr(up)),
                         (WEIGHT, 1, Padding(FocusAttr(month), align='center', width='pack')),
                         (4, FocusAttr(year)),
                         ])
        return Fixed(Pile([title, Days(self._date, self)]), 20)


class DayOfMonth(DateKeyPressMixin, MutableStatefulText):

    def __init__(self, state):
        MutableStatefulText.__init__(self, state)
        DateKeyPressMixin.__init__(self, 'd')

    def _state_as_text(self):
        return '%02d' % self.state.day


class DayOfMonthBar(OnFocus):

    def __init__(self, state, bar=None):
        super().__init__(DayOfMonth(state),
                         '+/spc/enter/d to inc day; -/D to dec; m/y to inc month/year; M/Y to dec; = now', bar)
        self.widget = self._w


class DayOfWeek(DateKeyPressMixin, MutableStatefulText):

    def __init__(self, state):
        MutableStatefulText.__init__(self, state)
        DateKeyPressMixin.__init__(self, 'D')

    def _state_as_text(self):
        return DAYS3[self.state.weekday()]


class DayOfWeekBar(OnFocus):

    def __init__(self, state, bar=None):
        super().__init__(DayOfWeek(state),
                         '+/spc/enter/d to inc day; first letter to advance; = now', bar)
        self.widget = self._w


class TextDate(BaseDate):

    def _make(self):
        down = QuickChangeBar(self._date, '<', -1, bar=self._bar)
        connect_signal(down.widget, 'change', self.date_change)
        up = QuickChangeBar(self._date, '>', 1, bar=self._bar)
        connect_signal(up.widget, 'change', self.date_change)
        year = YearBar(self._date, bar=self._bar)
        connect_signal(year.widget, 'change', self.date_change)
        month = MonthBar(self._date, as_text=False, bar=self._bar)
        connect_signal(month.widget, 'change', self.date_change)
        day_of_month = DayOfMonthBar(self._date, bar=self._bar)
        connect_signal(day_of_month.widget, 'change', self.date_change)
        day_of_week = DayOfWeekBar(self._date, bar=self._bar)
        connect_signal(day_of_week.widget, 'change', self.date_change)
        return Columns([(1, FocusAttr(down)),
                        (1, Text(" ")),
                        (4, Padding(FocusAttr(year), align='center', width='pack')),
                        (1, Text("-")),
                        (2, Padding(FocusAttr(month), align='center', width='pack')),
                        (1, Text("-")),
                        (2, Padding(FocusAttr(day_of_month), align='center', width='pack')),
                        (1, Text(" ")),
                        (3, Padding(FocusAttr(day_of_week), align='center', width='pack')),
                        (1, Text(" ")),
                        (1, FocusAttr(up)),
                        ])
