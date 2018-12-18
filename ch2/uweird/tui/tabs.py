from collections import OrderedDict
from collections.abc import Sequence

from urwid import emit_signal, connect_signal, Widget, ExitMainLoop, disconnect_signal

from .focus import Focus, FocusAttr, FocusWrap
from ...lib.utils import force_iterable


# new tab manager design

# tabs can be arranged in groups.  group contents can be wiped and re-added.
# this allows tabs in the "middle" of a traverse to be rebuilt.
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

# the widget tree traversal depends on code following conventions that
# i am inferring from the urwid code, but which aren't explicit anywhere.
# in particular, ever widget subclass should either:
# - be a decorator, in which case base_widget is used
# - or be a collection, exposing contents and focus_position
# the only exceptions are "leaf" widgets - tabs wil not move inside these.

# to get this functionality with wrapped widgets, use FocusWrap.


class Tab(FocusWrap):
    """
    A widget wrapper that is added automatically by TagList.add().  Must
    be added to any node that is both target and source of tabbing.
    Intercepts tab keypresses and raises a signal that causes the focus to
    change.

    Normal use is:
        tabs = TabList()
        ...
        widget = tabs.add(Widget(...))
    """

    def __init__(self, w):
        super().__init__(w)

    signals = ['tab']

    def keypress(self, size, key):
        # todo - pass to super first and only handle tabs that are not handled
        # by the widget?
        if key in ('tab', 'shift tab'):
            emit_signal(self, 'tab', self, key)
        else:
            return super().keypress(size, key)


class TabList(Sequence):
    """
    A list of tabbed widgets (in tabbing order) that will be managed by a TabNode.
    The list allows these to be assembled before the TabNode instance is created.
    May include both widgets and other TabNode instances.
    """

    def __init__(self):
        """
        Create an empty list.
        """
        self.__tabs = []

    def __wrap(self, widget_or_node):
        ignore = isinstance(widget_or_node, TabNode) or isinstance(widget_or_node, Tab)
        return widget_or_node if ignore else Tab(FocusAttr(widget_or_node))

    def append(self, widget_or_node):
        """
        Add a widget to the list of managed widgets.  The return value should be
        used in the constructed tree of widgets (it contains both a Tab target and
        a FocusAttr).
        """
        # todo - how do we modify FocusAttr?
        widget_or_node = self.__wrap(widget_or_node)
        self.__tabs.append(widget_or_node)
        return widget_or_node

    def remove(self, tab):
        self.__tabs.remove(tab)

    def insert(self, index, widget_or_node):
        widget_or_node = self.__wrap(widget_or_node)
        self.__tabs.insert(index, widget_or_node)
        return widget_or_node

    def insert_many(self, index, tab_list):
        for tab in reversed(tab_list):
            self.__tabs.insert(index, self.__wrap(tab))
        return tab_list

    def __getitem__(self, item):
        return self.__tabs[item]

    def __setitem__(self, index, item):
        self.__tabs[index] = item

    def __len__(self):
        return len(self.__tabs)


class TabNode(FocusWrap):
    """
    A widget wrapper that encapsulates a (local) root node in the widget tree and
    manages all the tabs below that node.

    In dynamic applications the entire TabList may be replaced using replace_all().
    If only a subset of all nodes need to be replaced, use a nested TabNode (so
    the entire contents of the nested node are replaced).

    Normal use is:

        tabs = TabList()
        widget1 = tabs.append(Widget(...))
        ...
        widgetN = tabs.append(Widget(...))
        root = TabNode(Container([widget1, ... windgetN]), tabs)
        root.discover()
    """

    signals = ['tab']

    def __init__(self, log, widget, tab_list):
        """
        Create a (local) root to the widget tree that manages tabs to the widgets
        below (possibly via nested TabNode instances).
        """
        super().__init__(widget)
        self.__log = log
        self.__tabs_and_indices = {}
        self.__focus = OrderedDict()
        self.__root = None
        self.__path = None
        self.__build_data(tab_list)

    def __build_data(self, tab_list):
        for tab in tab_list:
            n = len(self)
            self.__tabs_and_indices[tab] = n
            self.__tabs_and_indices[n] = tab
            self.__focus[tab] = None
            disconnect_signal(tab, 'tab', self.tab)
            connect_signal(tab, 'tab', self.tab)

    def __to_tab_list(self):
        tab_list = TabList()
        for i in range(len(self)):
            tab_list.append(self.__tabs_and_indices[i])
        return tab_list

    def replace(self, tabs):
        """
        Replace all the managed tabs.  Typically used at the local root of a dynamic
        section of the widget tree.
        """
        self.__tabs_and_indices = {}
        self.__focus = OrderedDict()
        self.__build_data(tabs)
        self.discover(root=self.__root, path=self.__path)

    def insert(self, index, tab):
        """
        Add a tab at the index give (so insert(0, tab) is at start)
        """
        tab_list = self.__to_tab_list()
        tab_list.insert(index, tab)
        self.replace(tab_list)

    def insert_many(self, index, tabs):
        tab_list = self.__to_tab_list()
        tab_list.insert_many(index, tabs)
        self.replace(tab_list)

    def __len__(self):
        return len(self.__focus)

    def tab(self, tab, key):
        """
        The target for tab signals from managed Tab() instances.

        On receiving a signal:
        * check whether tabbing can be handled locally and, if so, activate
        * check if we are root and, if so, loop around
        * otherwise re-raise to tab to remote neighbours (from nested node)
        """
        delta = 1 if key == 'tab' else -1
        n = self.__tabs_and_indices[tab] + delta
        if 0 <= n < len(self):
            self.__try_set_focus(n, key)
        elif not self.__path:
            self.to(None, key)  # loop around
        else:
            emit_signal(self, 'tab', self, key)

    def __try_set_focus(self, n, key):
        try:
            self.__log.debug('Trying to set focus on %s' % self.__tabs_and_indices[n])
            self.__set_focus(self.__tabs_and_indices[n], key)
        except AttributeError:
            self.discover(root=self.__root, path=self.__path)
            self.__set_focus(self.__tabs_and_indices[n], key)

    def __set_focus(self, tab, key):
        self.__log.debug('Using %s' % self.__focus[tab])
        self.__focus[tab].to(self.__root, key)

    def to(self, unused, key):
        """
        Replicate the Focus() interface.  This is used internally for sub-nodes.
        Instead of assigning focus using Focus.to(),
        """
        if self.__focus:
            n = 0 if key == 'tab' else len(self) - 1
            self.__log.debug('Re-targetting at %d' % n)
            self.__try_set_focus(n, key)
        else:
            # we have nothing to focus, so re-raise signal for remote neighbours
            self.__log.debug('Empty so raise signal')
            emit_signal(self, 'tab', self, key)

    def discover(self, root=None, path=None, discard=False):
        """
        Register the root widget here before use (in many cases the root node is
        also this TabNode, so no root argument is needed).

        Does a search of the entire widget tree, recording paths to added widgets
        so that they can be given focus quickly.
        """
        self.__root = root if root else self
        self.__path = path if path else []
        stack = [(self, self.__path)]  # only search sub-tree, not from root

        def unpack_container(widget, path):
            # contents can be dict, list or ListBox
            try:
                iterator = widget.contents.items()
            except AttributeError:
                try:
                    iterator = enumerate(widget.contents)
                except TypeError:
                    iterator = widget.contents.body.items()
            for (key, data) in iterator:
                # data can be widget or tuple containing widget
                yield force_iterable(data), list(path) + [key]

        def unpack_decorator(widget):
            if hasattr(widget, '_wrapped_widget'):
                self.__log.warning('Widget %s (type %s) doesn\'t expose contents' % (widget, type(widget)))
            elif hasattr(widget, 'base_widget'):
                if widget == widget.base_widget:
                    self.__log.debug('Widget with no focus: %s (type %s)' % (widget, type(widget)))
                else:
                    yield widget.base_widget

        def handle_new_widget(widget, path):
            if widget in self.__focus:
                if isinstance(widget, TabNode):
                    self.__focus[widget] = widget
                    widget.discover(self.__root, path=path)
                else:
                    self.__focus[widget] = Focus(path, self.__log)
            else:
                stack.append((widget, path))

        while stack:
            widget, path = stack.pop()
            try:
                for data, new_path in unpack_container(widget, path):
                    for datum in data:
                        if isinstance(datum, Widget):  # filter junk in data
                            handle_new_widget(datum, new_path)
            except AttributeError:
                for widget in unpack_decorator(widget):
                    handle_new_widget(widget, path)

        missing = list(filter(lambda x: self.__focus[x] is None, self.__focus))
        if missing:
            if discard:
                self.__log.info('Removing %s tabs' % len(missing))
                self.remove_many(missing)
            else:
                msg = map(lambda w: '%s (base type %s)' % (w, type(w._w.base_widget)), missing)
                raise Exception('Could not find %s' % ', '.join(msg))


class Root(TabNode):

    def __init__(self, log, widget, tab_list, quit='meta q', save='meta s', abort='meta x', session=None):
        super().__init__(log, widget, tab_list)
        self.__quit = quit
        self.__save = save
        self.__abort = abort
        self.__session = session

    def keypress(self, size, key):
        if key == self.__quit:
            self.save()
            raise ExitMainLoop()
        elif key == self.__abort:
            raise ExitMainLoop()
        elif key == self.__save:
            self.save()
        else:
            return super().keypress(size, key)

    def save(self):
        if self.__session:
            self.__session.flush()
            self.__session.commit()
