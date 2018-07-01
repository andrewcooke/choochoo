
from urwid import Edit, Columns, Pile, MainLoop, Filler, Divider, Frame, Text

from .utils import PALETTE
from .uweird.calendar import TextDate
from .uweird.decorators import Border
from .uweird.factory import Factory
from .uweird.focus import FocusWrap
from .uweird.tabs import Root
from .uweird.widgets import Nullable, SquareButton, ColText, ColSpace


class Definition(FocusWrap):

    def __init__(self, log, tabs, bar, binder, title='', description='', start=None, finish=None, sort=''):

        factory = Factory(tabs=tabs, bar=bar, binder=binder)
        title = factory(Edit(caption='Title: ', edit_text=title), bindto='title')
        start = factory(Nullable('Open', lambda date: TextDate(log, bar=bar, date=date), start, bar=bar),
                        bindto='start')
        finish = factory(Nullable('Open', lambda date: TextDate(log, bar=bar, date=date), finish, bar=bar),
                         bindto='finish')
        sort = factory(Edit(caption='Sort: ', edit_text=sort), bindto='sort')
        reset = factory(SquareButton('Reset'), message='reset from database', signal='click', target=binder.reset)
        save = factory(SquareButton('Save'), message='save to database', signal='click', target= binder.save)
        description = factory(Edit(caption='Description: ', edit_text=description, multiline=True),
                              bindto='description', default='')
        super().__init__(
            Pile([title,
                  Columns([(18, start),
                           ColText(' to '),
                           (18, finish),
                           ColSpace(),
                           ('weight', 3, sort),
                           ColSpace(),
                           (9, reset),
                           (8, save),
                           ]),
                  description,
                  ]))


class App(MainLoop):

    def __init__(self, log, title, msgbar, body, tab_list, saves):
        self.root = Root(log, Border(Frame(Filler(body, valign='top'),
                                           header=Pile([Text(title), Divider()]),
                                           footer=Pile([Divider(), msgbar]))),
                         tab_list, saves=saves)
        self.root.discover()
        super().__init__(self.root, palette=PALETTE)
