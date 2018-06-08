
from urwid import ListBox, Text, MainLoop, Frame, Padding, Filler, BoxAdapter, BigText, HalfBlock5x4Font

from .calendar import Calendar
from .utils import Border


def main(args):
    contents = Filler(Padding(Calendar(), width='clip'), height='pack')
    MainLoop(Border(Frame(contents, header=Text('Diary'))),
             palette=[('focus', 'bold', '')]).run()
