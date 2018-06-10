
from urwid import LineBox, AttrMap, WidgetWrap, Text


class Border(LineBox):
    """
    A blank border, one character in size.
    """

    def __init__(self, contents):
        super().__init__(contents, tlcorner=' ', tline=' ', lline=' ', trcorner=' ',
                         blcorner=' ', rline=' ', bline=' ', brcorner=' ')


class Focus:
    """
    Record focus from a complex container and then re-apply (eg when the widget
    has been rebuilt).
    """

    def __init__(self, w):
        self._focus = []
        try:
            while True:
                w = self._container(w)
                self._focus.append(w.focus_position)
                w = w.contents[w.focus_position][0]
        except IndexError:
            pass

    def apply(self, w):
        for f in self._focus:
            w = self._container(w)
            w.focus_position = f
            w = w.contents[f][0]

    def _container(self, w):
        while True:
            try:
                w.focus_position
                return w
            except Exception as e:
                if hasattr(w, '_original_widget'):
                    w = w._original_widget
                elif hasattr(w, '_wrapped_widget'):
                    w = w._wrapped_widget
                else:
                    raise e


class ImmutableFocusedText(WidgetWrap):
    """
    A text class where:
    - the text depends on some state
    - the appearance can change depending on focus
    """

    def __init__(self, state, plain=None, focus=None):
        self._text = Text('')
        self._text._selectable = True
        if plain is None: plain = 'plain'
        if focus is None: focus = plain + '-focus'
        super().__init__(AttrMap(self._text, plain, focus))
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


class MutableFocusedText(ImmutableFocusedText):
    """
    A text class where:
    - the text depends on some state
    - the appearance can change depending on focus
    - the state may be changed
    """

    def __init__(self, state, callback, plain=None, focus=None):
        super().__init__(state, plain=plain, focus=focus)
        self._callback = callback

    def _get_state(self):
        return self._state

    def _set_state(self, state):
        if state != self._state:
            self._state = state
            self._update_text()
            if self._callback: self._callback(state)

    state = property(_get_state, _set_state)


class Fixed(WidgetWrap):
    """
    Convert a widget to fixed size.  The height is whatever the widget
    flows to for the given width.
    """

    def __init__(self, w, width):
        super().__init__(w)
        self._size = w.pack((width,))

    def pack(self, size, focus=False):
        return self._size

    def render(self, size, focus=False):
        if size != tuple():
            raise Exception('Using fixed widget incorrectly (received size of %s)' % size)
        return super().render((self._size[0], ), focus)
