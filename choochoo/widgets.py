
from urwid import WidgetWrap, Edit, Columns, Pile

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
