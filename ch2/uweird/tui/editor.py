
from urwid import WEIGHT, connect_signal, Padding, Divider

from .fixed import Fixed
from .tabs import TabList, TabNode
from .widgets import DividedPile, SquareButton
from ...lib.widgets import App
from ...squeal.binders import Binder


class Editor(TabNode):
    '''
    An editor for simple database classes (Injury, ActivityGroup)
    '''

    # we have to be careful to work well with sqlalchemy's session semantics:
    # - general editing is done within a single session
    # - this includes reset, delete and adding empty new values
    #   (all can be done without session commit)
    # - to do this, we must keep a store of the windgets / binders
    #   so that we don't need to query (after initial loading)
    # - data are saved / discarded on final exit (only)

    def __init__(self, log, session, bar, Widget, Model):
        self.__log = log
        self.__session = session
        self.__bar = bar
        self.__Widget = Widget
        self.__Model = Model
        tabs = TabList()
        body = []
        for instance in self.__session.query(Model).order_by(Model.sort).all():
            widget = Widget(self.__log, tabs, self.__bar, self)
            widget.connect(Binder(self.__log, self.__session, widget, instance=instance))
            body.append(widget)
        # and a button to add blanks
        more = SquareButton('More')
        body.append(tabs.append(Padding(Fixed(more, 8), width='clip')))
        connect_signal(more, 'click', self.__add_blank)
        super().__init__(log, DividedPile(body), tabs)

    def __add_blank(self, _unused_widget):
        tabs = TabList()
        widget = self.__Widget(self.__log, tabs, self.__bar, self)
        widget.connect(Binder(self.__log, self.__session, widget, self.__Model))
        body = self._w.contents
        n = len(body)
        body.insert(n-1, (Divider(), (WEIGHT, 1)))
        body.insert(n-1, (widget, (WEIGHT, 1)))
        self._w.contents = body
        n = len(self)
        self.insert_many(n - 1, tabs)

    def remove(self, widget):
        body = self._w.contents
        index = list(map(lambda x: x[0], body)).index(widget)
        self.__log.debug('Index %d: %s' % (index, body[index]))
        del body[index]
        del body[index]
        self._w.contents = body
        self.discover(discard=True)


class EditorApp(App):

    def __init__(self, log, session, bar, name, Widget, Model):
        self.__session = session
        tabs = TabList()
        self.editor = tabs.append(Editor(log, session, bar, Widget, Model))
        super().__init__(log, name, bar, self.editor, tabs, session)

