
from urwid import WidgetWrap, Edit, Columns, Pile

from .uweird.calendar import TextDate
from .uweird.widgets import Nullable, SquareButton, ColText, ColSpace


class Definition(WidgetWrap):

    def __init__(self, tab_manager, binder, title='', description='', start=None, finish=None):
        title = tab_manager.add(binder.bind(Edit(caption='Title: ', edit_text=title), 'title'))
        start = tab_manager.add(binder.bind(Nullable('Open', TextDate, start), 'start'))
        finish = tab_manager.add(binder.bind(Nullable('Open', TextDate, finish), 'finish'))
        reset = tab_manager.add(binder.connect(SquareButton('Reset'), 'click', binder.reset))
        save = tab_manager.add(binder.connect(SquareButton('Save'), 'click', binder.save))
        description = tab_manager.add(binder.bind(Edit(caption='Description: ', edit_text=description), 'description', default=''))
        super().__init__(
            Pile([title,
                  Columns([(18, start),
                           ColText(' to '),
                           (18, finish),
                           ColSpace(),
                           (9, reset),
                           (8, save),
                           ]),
                  description,
                  ]))
