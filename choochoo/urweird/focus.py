
from urwid import AttrMap, Widget


class Focus:
    """
    Store and apply a focus path.
    """

    def __init__(self, focus):
        self._focus = focus

    def apply(self, widget):
        for focus in self._focus:
            widget = self._container(widget)
            try:
                widget.focus_position = focus
            except Exception:
                # the container may have changed
                # a common case is contents as list, so let's try setting to end of list
                try:
                    widget.focus_position = len(widget.contents) - 1
                except Exception:
                    return
            widget = self._find_widget(widget.contents[widget.focus_position])

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

    def _find_widget(self, widgets):
        if not isinstance(widgets, tuple):
            widgets = [widgets]
        for widget in widgets:
            if isinstance(widget, Widget):
                return widget
        raise Exception('No widget in %s' % str(widgets))


class FocusFor(Focus):
    """
    Record focus from a complex container and then re-apply (eg when the widget
    has been rebuilt).
    """

    def __init__(self, widget):
        focus = []
        try:
            while True:
                widget = self._container(widget)
                focus.append(widget.focus_position)
                widget = self._find_widget(widget.contents[widget.focus_position][0])
        except IndexError:  # as far down as we can go
            pass
        super().__init__(focus)


class FocusAttr(AttrMap):

    def __init__(self, w, plain=None, focus=None):
        if plain is None: plain = 'plain'
        if focus is None: focus = plain + '-focus'
        super().__init__(w, plain, focus)
