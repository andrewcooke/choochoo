
# https://github.com/urwid/urwid/issues/61

import urwid

a = urwid.Text(u"Text A")
b = urwid.Button(u"Button B")
c = urwid.Button(u"Button C")

grid = urwid.GridFlow([c,b], cell_width=36, h_sep=2, v_sep=1, align='left')
fill = urwid.Filler(grid, 'top')
loop = urwid.MainLoop(fill)
loop.run()
