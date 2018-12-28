
from urwid import Button, Text, emit_signal, connect_signal, Padding, Pile, Divider, WEIGHT, PACK, ACTIVATE

from .focus import FocusAttr, AttrChange, FocusWrap, OnFocus
from .state import MutableStatefulText
from .tabs import TabNode
from ...lib.utils import label


class SquareButton(Button):

    button_left = Text('[')
    button_right = Text(']')

    def __init__(self, label, on_press=None, user_data=None):
        super().__init__(label, on_press=on_press, user_data=user_data)
        self._w.dividechars = 0


class Nullable(FocusWrap):
    """
    make_widget must be able to generate a default state when called with no args.
    """

    signals = ['change']

    def __init__(self, replacement, make_widget, state=None, bar=None,
                 message='enter/spc to activate; del to reset'):
        self.__replacement = FocusAttr(SquareButton(replacement))
        self.__save_state = None
        if bar:
            self.__replacement = OnFocus(self.__replacement, message=message, bar=bar)
        self.__make_widget = make_widget
        super().__init__(self.__replacement)
        self.__set_state(state)

    def _invalidate(self):
        try:
            self._w.update_bar()  # message bar
        except AttributeError:
            pass
        super()._invalidate()

    def __set_state(self, state):
        nulled = self._w == self.__replacement
        if state is None:
            if not nulled:
                self.__save_state = self._w.state
            self._w = self.__replacement
        else:
            if nulled:
                self._w = self.__make_widget(self.__save_state)
                connect_signal(self._w, 'change', self._bounce_change)  # todo weak ref here?
            self._w.state = state

    def __get_state(self):
        if self._w == self.__replacement:
            return None
        else:
            return self._w.state

    state = property(__get_state, __set_state)

    def keypress(self, size, key):
        if self._w == self.__replacement:
            if self._command_map[key] == 'activate':
                self._w = self.__make_widget(self.__save_state)
                self._bounce_change(self._w, self._w.state)
                self._invalidate()
                return
        else:
            if key in ('delete', 'backspace'):
                self.__save_state = self._w.state
                self._w = self.__replacement
                self._bounce_change(self._w, None)
                self._invalidate()
                return
        try:
            return self._w.keypress(size, key)
        except AttributeError:
                return key

    def _bounce_change(self, unused_widget, value):
        emit_signal(self, 'change', self, value)


def ColText(text, format=None):
    """
    Shorthand for fixed width, literal column.
    """
    n = len(text)
    if format:
        text = [format(text)]
    return n, Text(text)


def ColSpace(weight=1):
    """
    Shorthand for an empty, expanding column.
    """
    return WEIGHT, weight, Padding(Text(''))


def ColPack(widget):
    return PACK, widget


class Rating0(MutableStatefulText):
    '''
    0-9 based scale.
    '''

    def __init__(self, caption='', state=None):
        self._caption = caption
        super().__init__(state)

    def _state_as_text(self):
        if self.state is None:
            text = '_'
        else:
            text = str(self.state)
        return [self._caption, text]

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


class Rating1(Rating0):
    '''
    1-10 based scale.
    '''

    def keypress(self, size, key):
        if key == '0':
            key = '10'
        return super().keypress(size, key)


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

    def _state_as_text(self):
        if self.state is None:
            return [self._caption, '_', ' ', label(self._units)]
        else:
            return [self._caption, self._string, ' ', label(self._units)]

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
                # todo - add log and log this
                error = True
                self._set_state_internal(state, signal=False)
        else:
            self._set_state_internal(None)
        self._update_text()
        if error != self._error:
            self._error = error
            raise AttrChange(error)
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


class DividedPile(Pile):

    def __init__(self, widget_list, focus_item=None, divide=True):
        if divide:
            divided = []
            for i, widget in enumerate(widget_list):
                if i: divided.append(Divider())
                divided.append(widget)
            super().__init__(divided, focus_item=focus_item)
        else:
            super().__init__(widget_list, focus_item=focus_item)


class FilteredPile(DividedPile):

    def __init__(self, widget_list, focus_item=None, divide=False):
        super().__init__([w for w in widget_list if w is not None], focus_item=focus_item, divide=divide)


class DynamicContent(TabNode):

    def __init__(self, log, session, bar):
        self._log = log
        self._session = session
        self._bar = bar
        self.__attrs = []
        super().__init__(log, *self._make())

    def _make(self):
        # should return (node, tab_list)
        raise NotImplemented()

    def rebuild(self):
        node, tabs = self._make()
        self._w = node
        self.replace(tabs)
        self._invalidate()
        self._log.debug('Rebuilt %s' % self)


class KeyMenu(MutableStatefulText):

    def __init__(self, caption, options, state=None):
        self.__caption = caption
        # options are map from state to text
        self.__options = options
        ordered_pairs = list(sorted((text[0].lower(), key) for (key, text) in options.items()))
        self.__keys = [key for (prefix, key) in ordered_pairs]
        self.__prefixes = {}
        for (prefix, key) in ordered_pairs:
            if prefix not in self.__prefixes: self.__prefixes[prefix] = []
            self.__prefixes[prefix].append(key)
        if state is None:
            state = next(iter(self.__options.keys()))
        if state not in options:
            raise Exception('Illegal state')
        super().__init__(state)

    def _state_as_text(self):
        return self.__caption + self.__options[self.state]

    def __rotate(self, list, delta):
        if delta < 0:
            return list[-1:] + list[:-1]
        else:
            return list[1:] + list[:1]

    def keypress(self, size, key):
        current = self.__options[self.state][0].lower()
        lower = key.lower()
        delta = 1 if key == lower else -1
        if lower in self.__prefixes:
            if lower == current:
                self.__prefixes[lower] = self.__rotate(self.__prefixes[lower], delta)
            self.state = self.__prefixes[lower][0]
        elif self._command_map[key] == 'activate':
            self.state = self.__keys[(self.__keys.index(self.state) + 1) % len(self.__keys)]
        else:
            return key


class ArrowMenu(MutableStatefulText):

    signals = ['change', 'postchange', 'click']

    def __init__(self, caption, options, state=None):
        self.__caption = caption
        self.__options = options
        states = list(options.keys())
        self.__next = dict(zip(states[-1:] + states[:-1], states))
        self.__prev = dict(zip(states, states[-1:] + states[:-1]))
        if state is None:
            state = states[0]
        if state not in options:
            raise Exception('Illegal state')
        super().__init__(state)

    def keypress(self, size, key):
        if key == 'left':
            self.state = self.__prev[self.state]
        elif key == 'right':
            self.state = self.__next[self.state]
        elif self._command_map[key] == ACTIVATE:
            self._emit('click')
        else:
            return key

    def _state_as_text(self):
        if len(self.__next) > 1:
            l, r = '<', '>'
        else:
            l, r = '[', ']'
        return [self.__caption, l, self.__options[self.state], r]

