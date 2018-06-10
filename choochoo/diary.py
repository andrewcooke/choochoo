
from urwid import Text, MainLoop, Frame, Padding, Filler

from .calendar import Calendar
from .utils import Border


def main(args):
    contents = Filler(Padding(Calendar(), width='clip'), height='pack')
    MainLoop(Border(Frame(contents, header=Text('Diary'))),
             palette=[('focus', 'bold', ''),
                      ('unimportant', 'dark blue', '')
                      ]).run()
