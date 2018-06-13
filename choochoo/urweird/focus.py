
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
            widgets = widget.contents[widget.focus_position]
            try:
                iter(widgets)
            except TypeError:
                widgets = [widgets]
            for widget in widgets:
                if isinstance(widget, Widget):
                    break
            else:
                return

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


class FocusFor(Focus):
    """
    Record focus from a complex container and then re-apply (eg when the widget
    has been rebuilt).
    """

    def __init__(self, w):
        focus = []
        try:
            while True:
                w = self._container(w)
                focus.append(w.focus_position)
                w = w.contents[w.focus_position][0]
        except IndexError:
            pass
        super().__init__(focus)


class FocusAttr(AttrMap):

    def __init__(self, w, plain=None, focus=None):
        if plain is None: plain = 'plain'
        if focus is None: focus = plain + '-focus'
        super().__init__(w, plain, focus)
