
from collections.abc import Sequence

from urwid import WidgetWrap, emit_signal, connect_signal, Widget

from .focus import Focus, FocusAttr


# new tab manager design

# tabs can be arranged in groups.  group contents can be wiped and re-added.
# this allows tabs in the "middle" of a travers to be rebuilt.
# tabs are assembled in a TabList and then passed to a TabNode which
# contains the group.  the TabNode has to be a widget itself since it
# needs to re-raise signals for tabbing.  because it is a WidgetWrap we need
# the intermediate TabList to assemble the group contents (since the
# TabNode will often be created later).  groups can be nested (a TabNode
# can appear in a TabList) and will behave correctly.  the top-most TabNode
# must have discover() called to set signals for tab looping and to discover
# focuses.

# the functionality depends on Focus.apply taking a keypress argument which
# is duplicated by TabNodes.  on TabNodes this triggers internal logic.


class Tab(WidgetWrap):

    signals = ['tab']

    def keypress(self, size, key):
        if key in ('tab', 'shift tab'):
            emit_signal(self, 'tab', self, key)
        else:
            return super().keypress(size, key)


class TabList(Sequence):

    def __init__(self):
        self.__tabs = []

    def add(self, widget_or_node):
        is_node = isinstance(widget_or_node, TabNode)
        widget_or_node = widget_or_node if is_node else Tab(FocusAttr(widget_or_node))
        self.__tabs.append(widget_or_node)
        return widget_or_node

    def __getitem__(self, item):
        return self.__tabs[item]

    def __len__(self):
        return len(self.__tabs)


class TabNode(WidgetWrap):

    # because this raise signals themselves, they must be widgets.

    signals = ['tab']

    def __init__(self, widget, tab_list):
        super().__init__(widget)
        self.__tabs_and_indices = {}
        self.__focus = {}
        self.__root = None
        self.__top = False
        self.__build_data(tab_list)

    def __build_data(self, tab_list):
        for tab in tab_list:
            n = len(self.__focus)
            self.__tabs_and_indices[tab] = n
            self.__tabs_and_indices[n] = tab
            self.__focus[tab] = None
            connect_signal(tab, 'tab', self.tab)

    def replace_all(self, tab_list):
        self.__tabs_and_indices = {}
        self.__focus = {}
        self.__build_data(tab_list)

    def tab(self, tab, key):
        delta = 1 if key == 'tab' else -1
        n = self.__tabs_and_indices[tab] + delta
        if 0 <= n < len(self.__focus):
            self.__try_set_focus(n, key)
        elif self.__top:
            self.to(None, key)
        else:
            emit_signal(self, 'tab', self, key)

    def __try_set_focus(self, n, key):
        try:
            self.__set_focus(self.__tabs_and_indices[n], key)
        except AttributeError:
            self.discover(self.__root)
            self.__set_focus(self.__tabs_and_indices[n], key)

    def __set_focus(self, tab, key):
        self.__focus[tab].to(self.__root, key)

    def to(self, root, key):
        if self.__focus:
            n = 0 if key == 'tab' else len(self.__focus) - 1
            self.__try_set_focus(n, key)
        else:
            emit_signal(self, 'tab', self, key)

    def discover(self, root=None, top=True):
        """
        Register the root widget here before use (in many cases the root node is
        also a TabNode, so no root argument is needed).

        Does a search of the entire widget tree, recording paths to added widgets
        so that they can be given focus quickly.
        """
        if top:
            self.__top = True
        if root is None:
            root = self
        self.__root = root
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
                            if widget in self.__focus:
                                if isinstance(widget, TabNode):
                                    self.__focus[widget] = widget
                                    widget.discover(root, top=False)
                                else:
                                    self.__focus[widget] = Focus(new_path)
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
                    if widget in self.__focus:
                        if isinstance(widget, TabNode):
                            self.__focus[widget] = widget
                            widget.discover(root, top=False)
                        else:
                            self.__focus[widget] = Focus(path)
                    else:
                        stack.append((widget, path))
        for widget in self.__focus:
            if not self.__focus[widget]:
                raise Exception('Could not find %s' % widget)

