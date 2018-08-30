
from urwid import Edit, Pile, Columns, connect_signal

from .lib.io import tui
from .squeal.database import Database
from .squeal.tables.activity import Activity
from .uweird.editor import EditorApp
from .uweird.factory import Factory
from .uweird.focus import MessageBar, FocusWrap
from .uweird.widgets import SquareButton, ColSpace


class ActivityWidget(FocusWrap):

    def __init__(self, log, tabs, bar, outer):
        self.__outer = outer
        factory = Factory(tabs=tabs, bar=bar)
        self.title = factory(Edit(caption='Title: '))
        self.sort = factory(Edit(caption='Sort: '))
        self.delete = SquareButton('Delete')
        delete = factory(self.delete, message='delete from database')
        self.reset = SquareButton('Reset')
        reset = factory(self.reset, message='reset from database')
        self.description = factory(Edit(caption='Description: ', multiline=True))
        super().__init__(
            Pile([self.title,
                  Columns([(20, self.sort),
                           ColSpace(),
                           (10, delete),
                           (9, reset)
                           ]),
                  self.description,
                  ]))

    def connect(self, binder):
        connect_signal(self.reset, 'click', lambda widget: binder.reset())
        connect_signal(self.delete, 'click', lambda widget: self.__on_delete(widget, binder))

    def __on_delete(self, _unused_widget, binder):
        binder.delete()
        self.__outer.remove(self)


@tui
def activities(args, log):
    '''
# activities

    ch2 activities

The interactive editor for activities.  Allows addition, deletion and modification of activities.

Once added, activities can be imported and will appear in the diary.

To exit, alt-q (or, without saving, Alt-x).
    '''
    session = Database(args, log).session()
    EditorApp(log, session, MessageBar(), "Activities", ActivityWidget, Activity).run()
