
from urwid import Text, MainLoop, Frame, Padding, Filler, Pile, Columns, Divider, Edit

from .calendar import Calendar
from .urweird.decorators import Border
from .urweird.focus import FocusAttr
from .urweird.tabs import TabManager


def make(tab_manager):
    calendar = tab_manager.add(Calendar())
    notes = tab_manager.add(FocusAttr(Edit(caption="Notes: ")))
    return Filler(
        Pile([Divider(),
              Columns([(20, Padding(calendar, width='clip')),
                       ('weight', 1, notes)],
                      dividechars=2)]),
        valign='top')


def main(args):
    tab_manager = TabManager()
    diary = Border(Frame(make(tab_manager), header=Text('Diary')))
    tab_manager.discover(diary)
    MainLoop(diary,
             palette=[('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
                      ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
                      ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black')
                      ]).run()
