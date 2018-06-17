
from urwid import Text, MainLoop, Frame, WidgetWrap, Columns, Padding, Pile, Divider, \
    Filler, Edit

from .uweird.database import SingleTableStatic
from .database import Database
from .log import make_log
from .utils import PALETTE
from .uweird.calendar import TextDate
from .uweird.widgets import Nullable
from .uweird.decorators import Border
from .uweird.focus import FocusAttr
from .uweird.tabs import TabManager
from .uweird.widgets import SquareButton


class InjuryDefn(WidgetWrap):

    def __init__(self, title='', start=None, finish=None):
        self.title = Edit(caption='Title: ', edit_text=title)
        self.start = Nullable('Open', TextDate, start)
        self.finish = Nullable('Open', TextDate, finish)
        self.reset = SquareButton('Reset')
        self.save = SquareButton('Save')
        super().__init__(
            Pile([FocusAttr(self.title),
                  Columns([(18, self.start),
                           (6, Text("  to  ")),
                           (18, self.finish),
                           ('weight', 1, Padding(Text(''))),
                           (9, FocusAttr(self.reset)),
                           (8, FocusAttr(self.save)),
                           ]),
                  ]))


def make_bound_injury(db, log):
    binder = SingleTableStatic(db, log, 'injury')
    injury = InjuryDefn()
    binder.bind(injury.title, 'title')
    binder.bind(injury.start, 'start')
    binder.bind(injury.finish, 'finish')
    return injury, binder


def make_widget(db, log, tab_manager):
    body = []
    for row in db.db.execute('''select id, start, finish, title from injury'''):
        injury, binder = make_bound_injury(db, log)
        binder.read_row(row)
        body.append(injury)
    injury, _ = make_bound_injury(db, log)
    body.append(injury)
    body = Filler(Pile(body), valign='top')
    return Border(Frame(body, header=Text('Injury')))


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager()
    injury = make_widget(db, log, tab_manager)
    tab_manager.discover(injury)
    MainLoop(injury, palette=PALETTE).run()
