
from urwid import Text, MainLoop, Frame, Padding, Filler

from .urwid import Border
from .calendar import Calendar


def main(args):
    contents = Filler(Padding(Calendar(), width='clip'), height='pack')
    MainLoop(Border(Frame(contents, header=Text('Diary'))),
             palette=[('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
                      ('unimportant', 'dark blue', ''), ('unimportant-focus', 'light blue', 'black')
                      ]).run()
