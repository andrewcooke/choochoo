
from urwid import Button, Text, WidgetWrap

from .focus import FocusAttr


class SquareButton(Button):

    button_left = Text('[')
    button_right = Text(']')


class Nullable(WidgetWrap):
    """
    make_widget must be able to generate a default state when called with no args.
    """

    def __init__(self, replacement, make_widget, state=None):
        self.__replacement = FocusAttr(SquareButton(replacement))
        self.__make_widget = make_widget
        if state is None:
            super().__init__(self.__replacement)
        else:
            super().__init__(make_widget(state))

    def __set_state(self, state):
        if state is None:
            self._w = self.__replacement
        elif self._w == self.__replacement:
            self._w = self.__make_widget(state)
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
                self._invalidate()
                return
        else:
            if key in ('delete', 'backspace'):
                self._w = self.__replacement
                self._invalidate()
                return
        try:
            return self._w.keypress(size, key)
        except AttributeError:
                return key