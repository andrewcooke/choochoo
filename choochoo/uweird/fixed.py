
from urwid import FIXED

from .focus import FocusWrap


class Fixed(FocusWrap):
    """
    Convert a widget to fixed size.  The height is whatever the widget
    flows to for the given width.
    """

    _sizing = frozenset([FIXED])

    def __init__(self, w, width):
        super().__init__(w)
        self._size = w.pack((width,))

    def pack(self, size, focus=False):
        return self._size

    def render(self, size, focus=False):
        if size != ():
            raise Exception('Using fixed widget incorrectly (received size of %s)' % size)
        return super().render((self._size[0], ), focus)
