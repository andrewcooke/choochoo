
from urwid import Text, MainLoop, Frame, Pile, Divider, \
    Filler, WEIGHT

from .widgets import Definition
from .database import Database
from .log import make_log
from .utils import PALETTE
from .uweird.database import SingleTableStatic, DATE_ORDINAL
from .uweird.decorators import Border
from .uweird.tabs import TabList, TabNode


def make_bound_injury(db, log, tabs, insert_callback=None):
    binder = SingleTableStatic(db, log, 'injury',
                               transforms={'start': DATE_ORDINAL, 'finish': DATE_ORDINAL},
                               insert_callback=insert_callback)
    injury = Definition(tabs, binder)
    return injury, binder


def make_widget(db, log, tabs):
    body = []
    for row in db.db.execute('select id, start, finish, title, sort, description from injury'):
        if body: body.append(Divider())
        injury, binder = make_bound_injury(db, log, tabs)
        binder.read_row(row)
        body.append(injury)

    pile = Pile(body)

    def insert_callback(pile=pile):
        contents = pile.contents
        injury, _ = make_bound_injury(db, log, tabs, insert_callback=insert_callback)
        if contents: contents.append((Divider(), (WEIGHT, 1)))
        contents.append((injury, (WEIGHT, 1)))
        pile.contents = contents

    insert_callback()  # initial empty
    return Border(Frame(Filler(Pile([Divider(), pile]), valign='top'),
                        header=Text('Injuries')))


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tabs = TabList()
    injury = TabNode(make_widget(db, log, tabs), tabs)
    injury.discover()
    MainLoop(injury, palette=PALETTE).run()
