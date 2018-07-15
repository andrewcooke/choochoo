
from urwid import WEIGHT, Edit, Pile, Columns, connect_signal

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

    def __init__(self, log, tabs, bar):

        factory = Factory(tabs=tabs, bar=bar)
        self.title = factory(Edit(caption='Title: '))
        self.start = factory(Nullable('Open', lambda date: TextDate(log, bar=bar), bar=bar))
        self.finish = factory(Nullable('Open', lambda date: TextDate(log, bar=bar), bar=bar))
        self.sort = factory(Edit(caption='Sort: '))
        self.raw_reset = SquareButton('Reset')
        self.reset = factory(self.raw_reset, message='reset from database')
        self.description = factory(Edit(caption='Description: ', multiline=True))
        super().__init__(
            Pile([self.title,
                  Columns([(18, self.start),
                           ColText(' to '),
                           (18, self.finish),
                           ColSpace(),
                           (WEIGHT, 3, self.sort),
                           ColSpace(),
                           (9, self.reset),
                           ]),
                  self.description,
                  ]))

    def connect(self, binder):
        connect_signal(self.raw_reset, 'click', lambda widget: binder.refresh())


class Injuries(DynamicContent):

    def _make(self):
        tabs = TabList()
        body = []
        for injury in self._session.query(Injury).order_by(Injury.sort).all():
            widget = InjuryWidget(self._log, tabs, self._bar)
            widget.connect(Binder(self._log, self._session, widget, Injury, defaults={'id': injury.id}))
            body.append(widget)
        # and a blank entry to be added if necessary
        widget = InjuryWidget(self._log, tabs, self._bar)
        widget.connect(Binder(self._log, self._session, widget, Injury))
        body.append(widget)
        return DividedPile(body), tabs


class InjuryApp(App):

    def __init__(self, log, session, bar):
        self.__session = session
        tabs = TabList()
        self.injuries = tabs.append(Injuries(log, session, bar))
        super().__init__(log, 'Diary', bar, self.injuries, tabs, session)

    def rebuild(self, unused_widget, unused_value):
        self.__session.commit()
        self.injuries.rebuild()
        self.root.discover()


def main(args):
    log = make_log(args)
    session = Database(args, log).session()
    InjuryApp(log, session, MessageBar()).run()
