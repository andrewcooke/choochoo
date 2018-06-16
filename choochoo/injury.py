
from urwid import Text, MainLoop, Frame, WidgetWrap, ListBox, SimpleFocusListWalker, Columns, Padding

from .uweird.calendar import TextDate
from .utils import PALETTE
from .database import Database
from .log import make_log
from .uweird.decorators import Border
from .uweird.tabs import TabManager


class Injury(WidgetWrap):

    def __init__(self):
        super().__init__(Columns([(18, TextDate()),
                                  (6, Text("  to  ")),
                                  (18, TextDate()),
                                  ('weight', 1, Padding(Text('')))]))


def make_widget(db, log, tab_manager):
    body = ListBox(SimpleFocusListWalker([Injury(), Injury(), Injury()]))
    return Border(Frame(body, header=Text('Injury')))


def main(args):
    log = make_log(args)
    db = Database(args, log)
    tab_manager = TabManager()
    injury = make_widget(db, log, tab_manager)
    tab_manager.discover(injury)
    MainLoop(injury, palette=PALETTE).run()
