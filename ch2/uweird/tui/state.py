
from urwid import Text, emit_signal

from .focus import FocusWrap


class ImmutableStatefulText(FocusWrap):
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

    def _state_as_text(self):
        return str(self.state)

    def _update_text(self):
        self._text.set_text(self._state_as_text())
        self._invalidate()

    def keypress(self, size, key):
        # need this because selectable
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
        self._set_state_external(state)

    def _set_state_external(self, state):
        self._set_state_internal(state)

    def _set_state_internal(self, state, signal=True):
        if state != self._state:
            old_state = self._state
            self._state = state
            # argument list to match Edit behaviour
            if signal:
                emit_signal(self, 'change', self, state)
            self._update_text()
            # this is similar behaviour to the edit widget
            if signal:
                emit_signal(self, 'postchange', self, old_state)

    state = property(_get_state, _set_state)
