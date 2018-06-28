
from urwid import Button, Text, emit_signal, connect_signal, Padding

from .state import MutableStatefulText
from .focus import FocusAttr, AttrChange, FocusWrap


class SquareButton(Button):

    button_left = Text('[')
    button_right = Text(']')


class Nullable(FocusWrap):
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


def ColSpace():
    """
    Shorthand for an empty, expanding column.
    """
    return 'weight', 1, Padding(Text(''))


class NonableInt(MutableStatefulText):

    def __init__(self, caption='', state=None):
        self._caption = caption
        super().__init__(state)

    def state_as_text(self):
        if self.state is None:
            text = '_'
        else:
            text = str(self.state)
        return self._caption + text


class Rating(MutableStatefulText):

    def __init__(self, caption='', state=None):
        self._caption = caption
        super().__init__(state)

    def state_as_text(self):
        if self.state is None:
            text = '_'
        else:
            text = str(self.state)
        return self._caption + text

    def keypress(self, size, key):
        if self._command_map[key] == 'activate':
            key = '+'
        if len(key) == 1 and '0' <= key <= '9':
            self.state = int(key)
        elif key in '+-':
            if self.state is None:
                self.state = 5
            else:
                self.state = min(9, max(0, self.state + (1 if key == '+' else -1)))
        elif key in ('delete', 'backspace'):
            self.state = None
        else:
            return key


class Number(MutableStatefulText):

    def __init__(self, caption='', state=None, minimum=0, maximum=100, type=int, decimal=False, dp=2, units=''):
        self._caption = caption
        self._min = minimum
        self._max = maximum
        self._type = type
        self._decimal = decimal
        self._dp = dp
        self._units = units
        # always start in non-error (partly because we cannot set error attr here)
        if state is None:
            self._error = False
            self._string = ''
        else:
            state = min(maximum, max(minimum, state))
            self._error = False
            self._string = str(state)
        super().__init__(state)

    def _set_state_external(self, state):
        if state is None:
            self._string = ''
        else:
            state = min(self._max, max(self._min, state))
            self._string = str(state)
        self._set_state_internal(state)

    def state_as_text(self):
        if self.state is None:
            return self._caption + '_'
        else:
            return self._caption + self._string + self._units

    def _update_string(self, key):
        used = False
        if self._command_map[key] == 'activate' and self._error:
            if self.state is not None:
                self._string = str(self.state)
            else:
                self._string = ''
            used = True
        elif key == '-' and self._string:
            if self._string.startswith('-'):
                self._string = self._string[1:]
            else:
                self._string = '-' + self._string
            used = True
        elif len(key) == 1 and '0' <= key <= '9':
            if not self._decimal or '.' not in self._string or self._current_dp() < self._dp:
                self._string += key
            used = True
        elif self._decimal and key == '.' and '.' not in self._string:
            self._string += key
            used = True
        elif key in ('backspace', 'delete'):
            if self._string:
                self._string = self._string[:-1]
                used = True
        return used

    def _current_dp(self):
        try:
            (pre, post) = self._string.split('.')
            return len(post)
        except ValueError:
            return 0

    def _check_string(self):
        error = False
        if self._string:
            try:
                if self._decimal and self._current_dp() > self._dp:
                    raise Exception('Too many decimal places')
                state = self._type(self._string)
                if self._min <= state <= self._max:
                    self._set_state_internal(state)
                else:
                    raise Exception('Out of range')
            except Exception as e:
                error = True
        else:
            self._set_state_internal(None)
        self._update_text()
        if error != self._error:
            self._error = error
            raise AttrChange(error)
            pass
        return

    def keypress(self, size, key):
        if self._update_string(key):
            self._check_string()
        else:
            return key


class Integer(Number):

    def __init__(self, caption='', state=None, minimum=0, maximum=100, units=''):
        super().__init__(caption=caption, state=state, minimum=minimum, maximum=maximum,
                         units=units)


class Float(Number):

    def __init__(self, caption='', state=None, minimum=0, maximum=100, dp=2, units=''):
        super().__init__(caption=caption, state=state, minimum=minimum, maximum=maximum,
                         type=float, decimal=True, dp=dp, units=units)
