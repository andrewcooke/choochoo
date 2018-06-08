
from urwid import LineBox


class Border(LineBox):

    def __init__(self, contents):
        super().__init__(contents, tlcorner=' ', tline=' ', lline=' ', trcorner=' ',
                         blcorner=' ', rline=' ', bline=' ', brcorner=' ')
