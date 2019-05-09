
import time as t
from itertools import zip_longest
from pprint import PrettyPrinter
from re import split

from ..stoats.names import M, KM, PC

PALETTE_RAINBOW = [
    ('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
    ('em', 'white', 'black'),
    ('label', 'dark gray', 'black'),
    ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
    ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black'),
    ('error', 'dark red', 'black'), ('error-focus', 'light red', 'black'),
    ('bar', 'dark gray', 'black'), ('bar-focus', 'dark gray', 'black'),
    ('rank-1', 'light red', 'black'), ('rank-2', 'yellow', 'black'), ('rank-3', 'dark green', 'black'),
    ('rank-4', 'light blue', 'black'), ('rank-5', 'light gray', 'black'),
    ('zone-6', 'black', 'white'), ('zone-5', 'black', 'light red'), ('zone-4', 'black', 'yellow'),
    ('zone-3', 'black', 'dark green'), ('zone-2', 'black', 'light blue'), ('zone-1', 'black', 'light gray'),
    ('quintile-1', 'light gray', 'black'), ('quintile-2', 'light blue', 'black'), ('quintile-3', 'dark green', 'black'),
    ('quintile-4', 'yellow', 'black'), ('quintile-5', 'light red', 'black'),
]


def sign(x):
    if x == 0:
        return 0
    elif x > 0:
        return 1
    else:
        return -1


def sigfig(value, n=2):
    scale = 1
    while value >= 10 ** n:
        value /= 10
        scale *= 10
    while value < 10 ** (n-1):
        value *= 10
        scale /= 10
    return int(0.5 + value) * scale


def em(text):
    return 'em', text


def error(text):
    return 'error', text


def label(text):
    return 'label', text


def force_iterable(data):
    try:
        iter(data)
        return data
    except TypeError:
        return [data]


def unique(elements, key=lambda x: x):
    known = set()
    for element in elements:
        value = key(element)
        if value not in known:
            known.add(value)
            yield element


def datetime_to_epoch(datetime):
    return datetime.timestamp()


def interleave(sep, iter):
    for started, value in enumerate(iter):
        if started:
            yield sep
        yield value


# https://docs.python.org/3/library/itertools.html#itertools-recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


PP = PrettyPrinter(indent=0, depth=1, width=80, compact=True)


def short_str(x):
    text = PP.pformat(x)
    lines = text.splitlines(False)
    if len(lines) > 1:
        return lines[0][:20] + '...' + lines[-1][-20:]
    else:
        return text


def format_metres(dist):
    if dist < 1000:
        return str(int(dist)) + M
    else:
        return f'{dist/1000:.1f}{KM}'


def format_percent(pc):
    if pc > 0.5:
        return f'{pc:.1f}{PC}'
    else:
        return f'{pc:.2f}{PC}'

