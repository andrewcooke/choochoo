
from urwid import Button, Text, WidgetWrap, emit_signal, connect_signal

from .state import MutableStatefulText
from .focus import FocusAttr


class SquareButton(Button):

    button_left = Text('[')
    button_right = Text(']')


class Nullable(WidgetWrap):
    """
    make_widget must be able to generate a default state when called with no args.
    """

    signals = ['change']

    def __init__(self, replacement, make_widget, state=None):
        self.__replacement = FocusAttr(SquareButton(replacement))
        self.__make_widget = make_widget
        super().__init__(self.__replacement)
        self.__set_state(state)

    def __set_state(self, state):
        if state is None:
            self._w = self.__replacement
        elif self._w == self.__replacement:
            self._w = self.__make_widget(state)
            connect_signal(self._w, 'change', self._bounce_change)  # todo weak ref here?
        else:
            self._w.state = state
        self._invalidate()

    def __get_state(self):
        if self._w == self.__replacement:
            return None
        else:
            return self._w.state

    state = property(__get_state, __set_state)

    def keypress(self, size, key):
        if self._w == self.__replacement:
            if self._command_map[key] == 'activate':
                self._w = self.__make_widget()
                self._bounce_change('change', self._w, self._w.state)
                self._invalidate()
                return
        else:
            if key in ('delete', 'backspace'):
                self._w = self.__replacement
                self._bounce_change('change', self._w, None)
                self._invalidate()
                return
        try:
            return self._w.keypress(size, key)
        except AttributeError:
                return key

    def _bounce_change(self, signal_name, unused_widget, value):
        emit_signal(self, 'change', self, value)


def ColText(text):
    """
    Shorthand for fixed width, literal column.
    """
    return len(text), Text(text)


class Rating(MutableStatefulText):

    def __init__(self, caption='', state=0):
        self._caption = caption
        super().__init__(state)

    def state_as_text(self):
        return '%s%d' % (self._caption, self.state)

    def keypress(self, size, key):
        if self._command_map[key] == 'activate':
            key = '+'
        if len(key) == 1 and '0' <= key <= '9':
            self.state = int(key)
        elif key in '+-':
            self.state = min(9, max(0, self.state + (1 if key == '+' else -1)))
        else:
            return key


class Number(MutableStatefulText):

    def __init__(self, caption='', state=0, min=0, max=100):
        self._caption = caption
        self._min = min
        self._max = max
        super().__init__(state)

    def state_as_text(self):
        return '%s%d' % (self._caption, self.state)

    def keypress(self, size, key):
        if self._command_map[key] == 'activate':
            key = '+'
        if key == '+':
            self.state = min(self._max, self.state + 1)
        elif key == '-' and self._min < 0:
            self.state = min(self._max, max(self._min, -1 * self.state))
        elif key in ('backspace', 'delete'):
            self.state = self.state // 10
        elif len(key) == 1 and '0' <= key <= '9':
            delta = int(key)
            if self.state < 0: delta = -delta
            self.state = min(self._max, max(self._min, self.state * 10 + delta))
        else:
            return key

