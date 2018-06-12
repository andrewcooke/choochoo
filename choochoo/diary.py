
from urwid import Text, MainLoop, Frame, Padding, Filler, IntEdit, Pile, Columns, Divider, Edit

from .urweird.decorators import Border
from .calendar import Calendar


def make():
    cols = []
    for i in range(4):
        pile = []
        for j in range(4):
            pile.append(Divider())
            pile.append(('pack', IntEdit(caption='Foo')))
        cols.append(Pile(pile))
    cols.append((20, Filler(Padding(Calendar(), width='clip'), height='pack')))
    return Filler(Columns(cols, box_columns=[4]), valign='top')


def make2():
    return Filler(
        Pile([Divider(),
              Columns([(20, Padding(Calendar(), width='clip')),
                       ('weight', 1, Edit(caption="Notes: "))],
                      dividechars=2)]),
        valign='top')


def main(args):
    MainLoop(Border(Frame(make2(), header=Text('Diary'))),
             palette=[('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
                      ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
                      ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black')
                      ]).run()
