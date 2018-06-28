
from urwid import LineBox


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
