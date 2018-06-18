from random import randint, random

from urwid import WidgetWrap, emit_signal, connect_signal, Widget

from .focus import Focus, FocusAttr


class TabTarget(WidgetWrap):
    """
    Add keypress logic to widgets that are targets of tabbing.

    Do not use directly - use TabManager.add().
    """

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

    This works by introspection, so all widgets must follow the
    conventions of the urwid library.  Containers must be list or dict-like.
    Other widgets that wrap must use _original_widget or _wrapped_widget
    attributes.

    Currently does not handle changes to the widget tree (although
    changes internal to the targets are unimportant).
    """

    def __init__(self, log):
        self._log = log
        self._widgets_indices = {}
        self._focus = {}
        self._root = None
        self._groups = {}

    def add(self, widget, group=None, add_focus=True):
        """
        Add widgets in order here.

        The returned (wrapped) value should be used in TUI construction.

        WARNING: removal only works correctly (currently) if all tabs
        "to tail" from some point are removed and re-added.
        """
        if add_focus: widget = FocusAttr(widget)
        widget = TabTarget(widget)
        if group:
            if group not in self._groups: self._groups[group] = []
            self._groups[group].append(widget)
        assert widget not in self._widgets_indices
        n = len(self._focus)
        self._widgets_indices[widget] = n
        self._widgets_indices[n] = widget
        self._focus[widget] = None
        connect_signal(widget, 'tabforwards', self.forwards)
        connect_signal(widget, 'tabbackwards', self.backwards)
        assert widget in self._widgets_indices
        return widget

    def remove(self, group):
        self._log.debug('Removing group %s' % group)
        if group in self._groups:
            for widget in self._groups[group]:
                n = self._widgets_indices[widget]
                del self._widgets_indices[widget]
                del self._widgets_indices[n]
                del self._focus[widget]
            del self._groups[group]
        else:
            self._log.warn('Duplicate removal for group %s?' % group)

    def forwards(self, widget):
        """
        Signal target for tabbing forwards.
        """
        self._wards(widget, 1)

    def backwards(self, widget):
        """
        Signal target for tabbing backwards.
        """
        self._wards(widget, -1)

    def _wards(self, widget, delta):
        n = self._widgets_indices[widget]
        try:
            self._set_focus(self._widgets_indices[(n + delta) % len(self._focus)])
        except AttributeError:
            self.discover(self._root)
            self._set_focus(self._widgets_indices[(n + delta) % len(self._focus)])
        except KeyError:
            self._log.error('all: ' + str(self._widgets_indices))
            self._log.error('keys: ' + str(list(sorted(filter(lambda x: isinstance(x, int), self._widgets_indices.keys())))))
            self._log.error('values: ' + str(list(sorted(filter(lambda x: isinstance(x, int), self._widgets_indices.values())))))
            self._log.error('focus: ' + str(self._focus))
            raise

    def _set_focus(self, widget):
        self._focus[widget].apply(self._root)

    def discover(self, root):
        """
        Register the root widget here before use.

        Does a search of the entire widget tree, recording paths to added widgets
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
                    try:
                        # possibly a dict
                        iterator = enumerate(node.contents)
                    except TypeError:
                        # possibly a ListBox
                        iterator = node.contents.body.items()
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
