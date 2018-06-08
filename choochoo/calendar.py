
import datetime as dt
from calendar import month_name

from urwid import Columns, GridFlow, Pile, WidgetWrap, Text, BigText, Padding

MONTHS = month_name[1:]


class ImmutableFocusedText(Text):

    def __init__(self, state):
        self._state = state
        self._focus = False
        self._selectable = True
        super().__init__(self.state_as_text())

    @property
    def state(self):
        return self._state

    def state_as_text(self):
        return str(self.state)

    def _update_text(self):
        text = self.state_as_text()
        if self._focus:
            self.set_text(('focus', text))
        else:
            self.set_text(text)
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

    def __init__(self, state):
        super().__init__(state)
        self.changed = False

    def _update_state(self, state):
        if state != self._state:
            self._state = state
            self._update_text()
            self.changed = True


class Month(MutableFocusedText):

    def __init__(self, month):
        super().__init__(month)

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

    def __init__(self, year):
        super().__init__(year)

    def keypress(self, size, key):
        if '0' <= key <= '9':
            self._update_state(int(str(self.state)[:-1] + key))
            return
        if key in '-+':
            self._update_state(self.state + (1 if key == '+' else -1))
            return
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


class Calendar(WidgetWrap):

    def __init__(self, date=None):
        if not date: date = dt.date.today()
        title = Columns([Padding(Month(date.month - 1), align='center', width='pack'),
                         Padding(Year(date.year), align='center', width='pack')])
        days = GridFlow([ImmutableFocusedText(i) for i in range(1, 30)], 2, 1, 0, 'right')
        super().__init__(Fixed(Pile([title, days]), 20))

