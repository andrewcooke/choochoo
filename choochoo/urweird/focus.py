from urwid import AttrMap


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
            # the container may have changed size and if we're "off the end" then
            # we'll get an error.  so progressively retract until it works.
            while True:
                try:
                    w.focus_position = f
                    break
                except IndexError:
                    f -= 1
                    if f < 0: return  # give up
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


class FocusAttr(AttrMap):

    def __init__(self, w, plain=None, focus=None):
        if plain is None: plain = 'plain'
        if focus is None: focus = plain + '-focus'
        super().__init__(w, plain, focus)
