
from urwid import Text, MainLoop, Frame, Padding, Filler, Pile, Columns, Divider, connect_signal

from .database import Database
from .log import make_log
from .uweird.calendar import Calendar
from .uweird.database import SingleTableBinder, NoneProofEdit
from .uweird.decorators import Border
from .uweird.focus import FocusAttr
from .uweird.tabs import TabManager


def make_widget(binder, tab_manager):
    calendar = Calendar()
    connect_signal(calendar, 'change', binder.update_key)
    notes = NoneProofEdit(caption="Notes: ")
    binder.bind(notes, 'notes')
    body = Filler(
        Pile([Divider(),
              Columns([(20, Padding(tab_manager.add(calendar), width='clip')),
                       ('weight', 1, tab_manager.add(FocusAttr(notes)))],
                      dividechars=2)]),
        valign='top')
    binder.update_key(None, calendar.date)
    return Border(Frame(body, header=Text('Diary')))


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager()
    binder = SingleTableBinder(db, log, 'diary', 'ordinal', key_transform=lambda x: x.toordinal())
    diary = make_widget(binder, tab_manager)
    tab_manager.discover(diary)
    MainLoop(diary,
             palette=[('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
                      ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
                      ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black')
                      ]).run()
