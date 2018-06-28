
from urwid import WidgetWrap, Edit, Columns, Pile, MainLoop, Filler, Divider, Frame, Text

from .utils import PALETTE
from .uweird.tabs import Root
from .uweird.decorators import Border
from .uweird.calendar import TextDate
from .uweird.widgets import Nullable, SquareButton, ColText, ColSpace


class Definition(WidgetWrap):

    def __init__(self, log, tabs, binder, title='', description='', start=None, finish=None, sort=''):
        title = tabs.append(binder.bind(Edit(caption='Title: ', edit_text=title), 'title'))
        start = tabs.append(binder.bind(Nullable('Open', lambda: TextDate(log), start), 'start'))
        finish = tabs.append(binder.bind(Nullable('Open', lambda: TextDate(log), finish), 'finish'))
        sort = tabs.append(binder.bind(Edit(caption='Sort: ', edit_text=sort), 'sort'))
        reset = tabs.append(binder.connect(SquareButton('Reset'), 'click', binder.reset))
        save = tabs.append(binder.connect(SquareButton('Save'), 'click', binder.save))
        description = tabs.append(binder.bind(Edit(caption='Description: ', edit_text=description, multiline=True),
                                                  'description', default=''))
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


class MessageBar(Text):

    def __init__(self):
        super().__init__('', wrap='clip')


class App(MainLoop):

    def __init__(self, log, title, msgbar, body, tab_list, saves):
        self.root = Root(log, Border(Frame(Filler(Pile([Divider(), body]), valign='top'),
                                           header=Pile([msgbar, Divider(), Text(title)]))),
                         tab_list, saves=saves)
        self.root.discover()
        super().__init__(self.root, palette=PALETTE)
