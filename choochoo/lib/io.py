
from shutil import get_terminal_size


def terminal_width(width=None):
    return get_terminal_size()[0] if width is None else width
