
from urwid import Text, MainLoop, Frame, Padding, Filler

from .urwid import Border
from .calendar import Calendar


def main(args):
    contents = Filler(Padding(Calendar(), width='clip'), height='pack')
    MainLoop(Border(Frame(contents, header=Text('Diary'))),
             palette=[('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
                      ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
                      ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black')
                      ]).run()
