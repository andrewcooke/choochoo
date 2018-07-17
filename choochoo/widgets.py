
from urwid import Edit, Columns, Pile, MainLoop, Filler, Divider, Frame, Text, WEIGHT

from .utils import PALETTE
from .uweird.calendar import TextDate
from .uweird.decorators import Border
from .uweird.factory import Factory
from .uweird.focus import FocusWrap
from .uweird.tabs import Root
from .uweird.widgets import Nullable, SquareButton, ColText, ColSpace


class App(MainLoop):

    def __init__(self, log, title, msgbar, body, tab_list, session):
        self.root = Root(log, Border(Frame(Filler(body, valign='top'),
                                           header=Pile([Text(title), Divider()]),
                                           footer=Pile([Divider(), msgbar]))),
                         tab_list, session=session)
        self.root.discover()
        super().__init__(self.root, palette=PALETTE)
