
from urwid import Text, MainLoop, Frame, Padding, Filler, Pile, Columns, Divider, Edit, WidgetWrap, connect_signal

from .database import Database
from .urweird.calendar import Calendar
from .urweird.decorators import Border
from .urweird.focus import FocusAttr
from .urweird.tabs import TabManager


class Diary(WidgetWrap):

    def __init__(self, db, tab_manager):
        self._db = db
        self._calendar = Calendar()
        self._notes = Edit(caption="Notes: ")
        super().__init__(
            Filler(
                Pile([Divider(),
                      Columns([(20, Padding(tab_manager.add(self._calendar), width='clip')),
                               ('weight', 1, tab_manager.add(FocusAttr(self._notes)))],
                              dividechars=2)]),
                valign='top'))
        self._date = self._calendar.date
        self._date_change(self._date)
        connect_signal(self._calendar, 'change', self._date_change)

    def _date_change(self, date):
        self._db.db.execute('update diary set notes = ? where ordinal = ?',
                            (self._notes.edit_text, self._date.toordinal()))
        self._date = date
        self._notes.edit_text = self._db.null_to_text(
            self._db.db.execute('select notes from diary where ordinal = ?', (date.toordinal(), )).fetchone())


def main(args):
    db = Database(args)
    tab_manager = TabManager()
    diary = Border(Frame(Diary(args, tab_manager), header=Text('Diary')))
    tab_manager.discover(diary)
    MainLoop(diary,
             palette=[('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
                      ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
                      ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black')
                      ]).run()
