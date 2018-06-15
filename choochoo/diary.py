
from urwid import Text, MainLoop, Frame, Padding, Filler, Pile, Columns, Divider, Edit, WidgetWrap, connect_signal

from .log import make_log
from .database import Database
from .uweird.calendar import Calendar
from .uweird.database import SingleTableBinder
from .uweird.decorators import Border
from .uweird.focus import FocusAttr
from .uweird.tabs import TabManager


class Diary(WidgetWrap):

    def __init__(self, log, binder, tab_manager):
        self._log = log
        self._calendar = Calendar()
        connect_signal(self._calendar, 'change', binder.update_key)
        self._notes = Edit(caption="Notes: ")
        binder.bind(self._notes, 'notes')
        super().__init__(
            Filler(
                Pile([Divider(),
                      Columns([(20, Padding(tab_manager.add(self._calendar), width='clip')),
                               ('weight', 1, tab_manager.add(FocusAttr(self._notes)))],
                              dividechars=2)]),
                valign='top'))
        binder.update_key(self._calendar.date)


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager()
    binder = SingleTableBinder(db, log, 'diary', 'ordinal', key_transform=lambda x: x.toordinal())
    diary = Border(Frame(Diary(log, binder, tab_manager), header=Text('Diary')))
    tab_manager.discover(diary)
    MainLoop(diary,
             palette=[('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
                      ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
                      ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black')
                      ]).run()
