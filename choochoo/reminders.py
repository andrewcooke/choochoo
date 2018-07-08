
from urwid import Divider, WEIGHT, Edit, Pile, Columns

from .database import Database
from .log import make_log
from .uweird.calendar import TextDate
from .uweird.database import SingleTableStatic, DATE_ORDINAL
from .uweird.factory import Factory
from .uweird.focus import MessageBar, FocusWrap
from .uweird.tabs import TabList
from .uweird.widgets import DividedPile, Nullable, SquareButton, ColText, ColSpace
from .widgets import App


class Reminder(FocusWrap):

    def __init__(self, log, tabs, bar, binder, title='', specification='', start=None, finish=None, sort=''):

        factory = Factory(tabs=tabs, bar=bar, binder=binder)
        title = factory(Edit(caption='Title: ', edit_text=title), bindto='title')
        spec = factory(Edit(caption='Spec: ', edit_text=specification), bindto='specification')
        start = factory(Nullable('Open', lambda date: TextDate(log, bar=bar, date=date), start, bar=bar),
                        bindto='start')
        finish = factory(Nullable('Open', lambda date: TextDate(log, bar=bar, date=date), finish, bar=bar),
                         bindto='finish')
        sort = factory(Edit(caption='Sort: ', edit_text=sort), bindto='sort')
        reset = factory(SquareButton('Reset'), message='reset from database', signal='click', target=binder.reset)
        save = factory(SquareButton('Save'), message='save to database', signal='click', target= binder.save)
        super().__init__(
            Pile([Columns([title,
                           spec
                           ]),
                  Columns([(18, start),
                           ColText(' to '),
                           (18, finish),
                           ColSpace(),
                           ('weight', 3, sort),
                           ColSpace(),
                           (9, reset),
                           (8, save),
                           ]),
                  ]))


def make_bound_reminder(db, log, tabs, bar, insert_callback=None):
    binder = SingleTableStatic(db, log, 'reminder',
                               transforms={'start': DATE_ORDINAL, 'finish': DATE_ORDINAL},
                               insert_callback=insert_callback)
    injury = Reminder(log, tabs, bar, binder)
    return injury, binder


def make_widget(db, log, tabs, bar, saves):
    body = []
    for row in db.db.execute('select id, start, finish, title, sort, specification from reminder'):
        reminder, binder = make_bound_reminder(db, log, tabs, bar)
        saves.append(binder.save)
        binder.read_row(row)
        body.append(reminder)

    pile = DividedPile(body)

    def insert_callback(saves=saves, pile=pile):
        contents = pile.contents
        reminder, binder = make_bound_reminder(db, log, tabs, bar, insert_callback=insert_callback)
        saves.append(binder.save)
        if contents: contents.append((Divider(), (WEIGHT, 1)))
        contents.append((reminder, (WEIGHT, 1)))
        pile.contents = contents

    insert_callback()  # initial empty

    return pile


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tabs = TabList()
    saves = []
    bar = MessageBar()
    injuries = App(log, 'Reminders', bar, make_widget(db, log, tabs, bar, saves), tabs, saves)
    injuries.run()
