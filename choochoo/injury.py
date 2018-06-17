
from urwid import Text, MainLoop, Frame, WidgetWrap, Columns, Padding, Pile, Divider, \
    Filler, Edit, connect_signal, WEIGHT

from .uweird.database import SingleTableStatic, DATE_ORDINAL
from .database import Database
from .log import make_log
from .utils import PALETTE
from .uweird.calendar import TextDate
from .uweird.widgets import Nullable
from .uweird.decorators import Border
from .uweird.focus import FocusAttr
from .uweird.tabs import TabManager
from .uweird.widgets import SquareButton


class InjuryDefn(WidgetWrap):

    def __init__(self, tab_manager, title='', start=None, finish=None):
        self.title = Edit(caption='Title: ', edit_text=title)
        self.start = Nullable('Open', TextDate, start)
        self.finish = Nullable('Open', TextDate, finish)
        self.reset = SquareButton('Reset')
        self.save = SquareButton('Save')
        super().__init__(
            Pile([tab_manager.add(FocusAttr(self.title)),
                  Columns([(18, tab_manager.add(self.start)),
                           (6, Text("  to  ")),
                           (18, tab_manager.add(self.finish)),
                           ('weight', 1, Padding(Text(''))),
                           (9, tab_manager.add(FocusAttr(self.reset))),
                           (8, tab_manager.add(FocusAttr(self.save))),
                           ]),
                  ]))


def make_bound_injury(db, log, tab_manager, insert_callback=None):
    binder = SingleTableStatic(db, log, 'injury',
                               transforms={'start': DATE_ORDINAL, 'finish': DATE_ORDINAL},
                               insert_callback=insert_callback)
    injury = InjuryDefn(tab_manager)
    binder.bind(injury.title, 'title')
    binder.bind(injury.start, 'start')
    binder.bind(injury.finish, 'finish')
    connect_signal(injury.save, 'click', binder.save)
    connect_signal(injury.reset, 'click', binder.reset)
    return injury, binder


def make_widget(db, log, tab_manager):
    body = []
    for row in db.db.execute('select id, start, finish, title from injury'):
        if body: body.append(Divider())
        injury, binder = make_bound_injury(db, log, tab_manager)
        binder.read_row(row)
        body.append(injury)

    pile = Pile(body)

    def insert_callback(pile=pile):
        contents = pile.contents
        injury, _ = make_bound_injury(db, log, tab_manager, insert_callback=insert_callback)
        if contents: contents.append((Divider(), (WEIGHT, 1)))
        contents.append((injury, (WEIGHT, 1)))
        pile.contents = contents

    insert_callback()  # initial empty
    return Border(Frame(Filler(Pile([Divider(), pile]), valign='top'),
                        header=Text('Injury')))


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager()
    injury = make_widget(db, log, tab_manager)
    tab_manager.discover(injury)
    MainLoop(injury, palette=PALETTE).run()
