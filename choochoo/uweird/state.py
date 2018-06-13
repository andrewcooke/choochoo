
from urwid import WidgetWrap, AttrMap, Text, emit_signal


class ImmutableStatefulText(WidgetWrap):
    """
    A text class where the text depends on some state
    """

    def __init__(self, state):
        self._text = Text('')
        self._text._selectable = True
        super().__init__(self._text)
        self._state = state
        self._selectable = True
        self._update_text()

    @property
    def state(self):
        return self._state

    def state_as_text(self):
        return str(self.state)

    def _update_text(self):
        self._text.set_text(self.state_as_text())
        self._invalidate()

    def keypress(self, size, key):
        return key


class MutableStatefulText(ImmutableStatefulText):
    """
    A text class where the text depends on some state and
    the state may be changed
    """

    signals = ['change', 'postchange']

    def _get_state(self):
        return self._state

    def _set_state(self, state):
        if state != self._state:
            old_state = self._state
            self._state = state
            emit_signal(self, 'change', state)
            self._update_text()
            # this is similar behaviour to the edit widget
            emit_signal(self, 'postchange', old_state)

    state = property(_get_state, _set_state)
