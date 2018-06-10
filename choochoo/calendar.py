
import datetime as dt
from calendar import month_name, day_abbr, Calendar, monthrange

from urwid import Columns, GridFlow, Pile, WidgetWrap, Text, Padding

from .utils import sign


MONTHS = month_name[1:]
DAYS = list(map(lambda d: day_abbr[d][:2], Calendar(0).iterweekdays()))


class ImmutableFocusedText(Text):

    def __init__(self, state, attrs=''):
        self._state = state
        self._attrs = attrs
        self._focus = False
        self._selectable = True
        super().__init__(self._text_and_attrs())

    @property
    def state(self):
        return self._state

    def _text_and_attrs(self):
        text = self.state_as_text()
        if self._focus:
            return 'focus, ' + self._attrs, text
        else:
            return self._attrs, text

    def state_as_text(self):
        return str(self.state)

    def _update_text(self):
        self.set_text(self._text_and_attrs())
        self._invalidate()

    def _update_focus(self, focus):
        if focus != self.focus:
            self._focus = focus
            self._update_text()

    def pack(self, size=None, focus=False):
        self._update_focus(focus)
        return super().pack(size, focus)

    def render(self, size, focus=False):
        self._update_focus(focus)
        return super().render(size, focus)

    def keypress(self, size, key):
        return key


class MutableFocusedText(ImmutableFocusedText):

    def __init__(self, state, callback):
        super().__init__(state)
        self._callback = callback

    def _update_state(self, state):
        if state != self._state:
            self._state = state
            self._update_text()
            self._callback(self._state)


class Month(MutableFocusedText):

    def __init__(self, month, callback):
        super().__init__(month, callback)

    def keypress(self, size, key):
        if 'a' <= key <= 'z':
            tries, month = 0, self.state
            while tries < 12:
                tries += 1
                month = (month + 1) % len(MONTHS)
                if MONTHS[month].lower().startswith(key):
                    self._update_state(month)
                    return
        if key in '-+':
            self._update_state((self.state + (1 if key == '+' else -1)) % len(MONTHS))
            return
        return key

    def state_as_text(self):
        return MONTHS[self.state]


class Year(MutableFocusedText):

    def __init__(self, year, callback):
        super().__init__(year, callback)

    def keypress(self, size, key):
        if '0' <= key <= '9':
            delta = int(key) - int(str(self.state)[-1])
            if abs(delta) > 5:
                delta -= sign(delta) * 10
            self._update_state(str(int(self.state) + delta))
            return
        if key in '-+':
            self._update_state(self.state + (1 if key == '+' else -1))
            return
        return key


class Day(ImmutableFocusedText):

    def __init__(self, state, callback):
        super().__init__(state)
        self._callback = callback

    def keypress(self, size, key):
        if key == ' ':
            self._callback(self.state)
        else:
            return key


class Fixed(WidgetWrap):

    def __init__(self, w, width):
        super().__init__(w)
        self._size = w.pack((width,))

    def pack(self, size, focus=False):
        return self._size

    def render(self, size, focus=False):
        if size != tuple():
            raise Exception('Using fixed widget incorrectly (received size of %s)' % size)
        return super().render((self._size[0], ), focus)


class Days(WidgetWrap):

    def __init__(self, date):
        super().__init__(self._make(date))
        self._date = date

    def _make(self, date):
        # if we do this as single gridflow then focus doesn't move down into dates
        names = GridFlow(list(map(lambda d: Text(d), DAYS)), 2, 1, 0, 'left')
        prev_month = (date.year if date.month > 1 else date.year - 1,
                      date.month - 1 if date.month > 1 else 12)
        prev_days = monthrange(*prev_month)[1]
        curr_days = monthrange(date.year, date.month)[1]
        first_day = dt.date(date.year, date.month, 1).weekday()  # mon 0
        total_days = first_day + curr_days
        extra_days = 7 - total_days % 7
        if extra_days == 7:
            extra_days = 0
        else:
            total_days += extra_days
        dates = [ImmutableFocusedText('%2s' % str(i), 'unimportant') for i in range(prev_days - first_day + 1, prev_days + 1)]
        dates.extend([ImmutableFocusedText('%2s' % str(i)) for i in range(1, curr_days + 1)])
        dates.extend([ImmutableFocusedText('%2s' % str(i), 'unimportant') for i in range(1, extra_days + 1)])
        dates = GridFlow(dates, 2, 1, 0, 'left')
        return Pile([names, dates])

    def keypress(self, size, key):
        super().keypress(size, key)
        day = self._w.focus.focus
        # if 'unimportant' in


class Calendar(WidgetWrap):

    def __init__(self, date=None):
        if not date: date = dt.date.today()
        self._date = date
        title = Columns([Padding(Month(date.month - 1, lambda m: self._date_changed(month=m + 1)),
                                 align='center', width='pack'),
                         Padding(Year(date.year, lambda y: self._date_changed(year=y)),
                                 align='center', width='pack')])
        super().__init__(Fixed(Pile([title, Days(date)]), 20))

    def _date_changed(self, day=None, month=None, year=None):
        print(day, month, year)
