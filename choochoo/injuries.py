
from urwid import WEIGHT, Edit, Pile, Columns, connect_signal, Padding, SolidFill, Text

from .log import make_log
from .squeal.binders import Binder
from .squeal.database import Database
from .squeal.injury import Injury
from .uweird.calendar import TextDate
from .uweird.factory import Factory
from .uweird.focus import MessageBar, FocusWrap
from .uweird.tabs import TabList
from .uweird.widgets import DividedPile, Nullable, SquareButton, ColSpace, ColText, DynamicContent
from .widgets import App


class InjuryWidget(FocusWrap):

    def __init__(self, log, tabs, bar, app=None):

        factory = Factory(tabs=tabs, bar=bar)
        self.__app = app
        self.title = factory(Edit(caption='Title: '))
        self.start = factory(Nullable('Open', lambda date: TextDate(log, bar=bar), bar=bar))
        self.finish = factory(Nullable('Open', lambda date: TextDate(log, bar=bar), bar=bar))
        self.sort = factory(Edit(caption='Sort: '))
        if app:
            self.__raw_add = SquareButton('Add')
            add = factory(self.__raw_add, message='add to database')
        self.__raw_reset = SquareButton('Reset')
        reset = factory(self.__raw_reset, message='reset from database')
        self.description = factory(Edit(caption='Description: ', multiline=True))
        super().__init__(
            Pile([self.title,
                  Columns([(18, self.start),
                           ColText(' to '),
                           (18, self.finish),
                           ColSpace(),
                           (WEIGHT, 3, self.sort),
                           ColSpace(),
                           (7, add if app else Text('')),  # to keep spacing regular
                           (9, reset)
                           ]),
                  self.description,
                  ]))

    def connect(self, binder):
        connect_signal(self.__raw_reset, 'click', lambda widget: binder.refresh())
        if self.__app:
            connect_signal(self.__raw_add, 'click', self.__app.rebuild)


class Injuries(DynamicContent):

    def __init__(self, log, session, bar, app):
        self.__app = app
        super().__init__(log, session, bar)

    def _make(self):
        tabs = TabList()
        body = []
        for injury in self._session.query(Injury).order_by(Injury.sort).all():
            widget = InjuryWidget(self._log, tabs, self._bar)
            widget.connect(Binder(self._log, self._session, widget, Injury, defaults={'id': injury.id}))
            body.append(widget)
        # and a blank entry to be added if necessary
        widget = InjuryWidget(self._log, tabs, self._bar, app=self.__app)
        widget.connect(Binder(self._log, self._session, widget, Injury))
        body.append(widget)
        return DividedPile(body), tabs


class InjuryApp(App):

    def __init__(self, log, session, bar):
        self.__session = session
        tabs = TabList()
        self.injuries = tabs.append(Injuries(log, session, bar, self))
        super().__init__(log, 'Diary', bar, self.injuries, tabs, session)

    def rebuild(self, unused_widget, unused_value):
        self.__session.commit()
        self.injuries.rebuild()
        self.root.discover()


def main(args):
    log = make_log(args)
    session = Database(args, log).session()
    InjuryApp(log, session, MessageBar()).run()
