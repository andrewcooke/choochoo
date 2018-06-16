
from urwid import Text, MainLoop, Frame, WidgetWrap, Columns, Padding, Pile, Divider, \
    Filler

from .database import Database
from .log import make_log
from .utils import PALETTE
from .uweird.calendar import TextDate
from .uweird.database import Nullable, NoneProofEdit
from .uweird.decorators import Border
from .uweird.focus import FocusAttr
from .uweird.tabs import TabManager
from .uweird.widgets import SquareButton


class InjuryDefn(WidgetWrap):

    def __init__(self, title=None, start=None, finish=None):
        self.title = NoneProofEdit(caption='Title: ', edit_text=title)
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


class InjuryDefnBinder:
    pass


def make_widget(db, log, tab_manager):
    for row in db.db.execute('''select id, start, finish, title from injury'''):
        pass
    body = Filler(Pile(
        [Divider(),
         InjuryDefn(),
         Divider(),
         InjuryDefn(),
         Divider(),
         InjuryDefn(),
         ]), valign='top')
    return Border(Frame(body, header=Text('Injury')))


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager()
    injury = make_widget(db, log, tab_manager)
    tab_manager.discover(injury)
    MainLoop(injury, palette=PALETTE).run()
