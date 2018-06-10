
from urwid import LineBox


class Border(LineBox):

    def __init__(self, contents):
        super().__init__(contents, tlcorner=' ', tline=' ', lline=' ', trcorner=' ',
                         blcorner=' ', rline=' ', bline=' ', brcorner=' ')


def sign(x):
    if x == 0:
        return 0
    elif x > 0:
        return 1
    else:
        return -1
