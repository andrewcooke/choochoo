
from urwid import WidgetWrap, emit_signal, connect_signal, Widget

from .focus import Focus


class TabTarget(WidgetWrap):

    signals = ['tabforwards', 'tabbackwards']

    def keypress(self, size, key):
        if key == 'tab':
            emit_signal(self, 'tabforwards', self)
        elif key == 'shift tab':
            emit_signal(self, 'tabbackwards', self)
        else:
            return super().keypress(size, key)


class TabManager:
    """
    Stand-alone, high-level (you get to choose which major widgets are
    included) tab-selection.  Call add() with the widgets in the tab
    order, and build with the returned (wrapped) widget.  Then register
    the root widget with discover().

    This works by introspection, so all widgets must follow the standards
    of the urwid library/.  Containers must be list or dict-like.  Other
    widgets that wrap must use _original_widget or _wrapped_widget
    attributes.

    Currently does not handle changes to the Widget tree (although
    changes internal to the targets are unimportant).
    """

    def __init__(self):
        self._widgets_indices = {}
        self._focus = {}
        self._root = None

    def add(self, widget):
        """
        Add widgets in order here.

        The returned (wrapped) value should be used in TUI construction.
        """
        widget = TabTarget(widget)
        assert widget not in self._widgets_indices
        n = len(self._focus)
        self._widgets_indices[widget] = n
        self._widgets_indices[n] = widget
        self._focus[widget] = None
        connect_signal(widget, 'tabforwards', self.forwards)
        connect_signal(widget, 'tabbackwards', self.backwards)
        return widget

    def forwards(self, widget):
        """
        Signal target for tabbing forwards.
        """
        n = self._widgets_indices[widget]
        self._set_focus(self._widgets_indices[(n + 1) % len(self._focus)])

    def backwards(self, widget):
        """
        Signal target for tabbing backwards.
        """
        n = self._widgets_indices[widget]
        self._set_focus(self._widgets_indices[(n - 1) % len(self._focus)])

    def _set_focus(self, widget):
        self._focus[widget].apply(self._root)

    def discover(self, root):
        """
        Register the root widget here before use.

        Does a search of teh entire widget tree, recording paths to added widgets
        so that they can be given focus quickly.
        """
        self._root = root
        stack = [(root, [])]
        while stack:
            node, path = stack.pop()
            try:
                # contents can be list or dict
                try:
                    iterator = node.contents.items()
                except AttributeError:
                    iterator = enumerate(node.contents)
                for (key, data) in iterator:
                    # data can be widget or tuple containing widget
                    try:
                        iter(data)
                    except TypeError:
                        data = [data]
                    new_path = list(path) + [key]
                    for widget in data:
                        if isinstance(widget, Widget):
                            if widget in self._focus:
                                self._focus[widget] = Focus(new_path)
                            else:
                                stack.append((widget, new_path))
            except AttributeError:
                if hasattr(node, '_original_widget'):
                    widget = node._original_widget
                elif hasattr(node, '_wrapped_widget'):
                    widget = node._wrapped_widget
                else:
                    widget = None
                if widget:
                    if widget in self._focus:
                        self._focus[widget] = Focus(path)
                    else:
                        stack.append((widget, path))
        for widget in self._focus:
            if not self._focus[widget]:
                raise Exception('Could not find %s' % widget)
