
from urwid import Pile, Divider, WEIGHT

from .database import Database
from .log import make_log
from .uweird.database import SingleTableStatic, DATE_ORDINAL
from .uweird.tabs import TabList
from .widgets import Definition, App


def make_bound_injury(db, log, tabs, insert_callback=None):
    binder = SingleTableStatic(db, log, 'injury',
                               transforms={'start': DATE_ORDINAL, 'finish': DATE_ORDINAL},
                               insert_callback=insert_callback)
    injury = Definition(log, tabs, binder)
    return injury, binder


def make_widget(db, log, tabs, saves):
    body = []
    for row in db.db.execute('select id, start, finish, title, sort, description from injury'):
        if body: body.append(Divider())
        injury, binder = make_bound_injury(db, log, tabs)
        saves.append(binder.save)
        binder.read_row(row)
        body.append(injury)

    pile = Pile(body)

    def insert_callback(saves=saves, pile=pile):
        contents = pile.contents
        injury, binder = make_bound_injury(db, log, tabs, insert_callback=insert_callback)
        saves.append(binder.save)
        if contents: contents.append((Divider(), (WEIGHT, 1)))
        contents.append((injury, (WEIGHT, 1)))
        pile.contents = contents

    insert_callback()  # initial empty

    return pile


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tabs = TabList()
    saves = []
    injuries = App(log, 'Injuries', make_widget(db, log, tabs, saves), tabs, saves)
    injuries.run()
