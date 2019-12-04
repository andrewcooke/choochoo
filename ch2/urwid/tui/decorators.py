
from urwid import LineBox, Columns

from .focus import FocusWrap
from .widgets import ColText


class Border(LineBox):
    """
    A blank border, one character in size.
    """

    def __init__(self, contents):
        super().__init__(contents, tlcorner=' ', tline=' ', lline=' ', trcorner=' ',
                         blcorner=' ', rline=' ', bline=' ', brcorner=' ')
        try:
            self.contents = self._w.contents
        except AttributeError:
            pass


class Indent(FocusWrap):
    """
    An indent on the left.
    """

    def __init__(self, contents, width=1):
        super().__init__(Columns([ColText(' ' * width), contents]))
        try:
            self.contents = self._w.contents
        except AttributeError:
            pass
