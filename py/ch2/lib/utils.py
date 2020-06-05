
from collections import defaultdict
from contextlib import contextmanager
from itertools import zip_longest, groupby
from logging import getLogger
from os import getpid, close, execl
from os.path import split, realpath, normpath, expanduser
from pprint import PrettyPrinter
from sys import executable, argv
from time import sleep

from psutil import Process

from .date import now
from ..names import Units


log = getLogger(__name__)


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

PALETTE_MINIMAL = [
    ('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
    ('em', 'white', 'black'),
    ('label', 'dark gray', 'black'),
    ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
    ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black'),
    ('error', 'dark red', 'black'), ('error-focus', 'light red', 'black'),
    ('bar', 'dark gray', 'black'), ('bar-focus', 'dark gray', 'black'),
    ('rank-1', 'white', 'black'), ('rank-2', 'light gray', 'black'), ('rank-3', 'light gray', 'black'),
    ('rank-4', 'light gray', 'black'), ('rank-5', 'light gray', 'black'),
    ('zone-6', 'black', 'white'), ('zone-5', 'black', 'white'), ('zone-4', 'black', 'white'),
    ('zone-3', 'black', 'light gray'), ('zone-2', 'black', 'dark gray'), ('zone-1', 'black', 'dark gray'),
    ('quintile-1', 'light gray', 'black'), ('quintile-2', 'light gray', 'black'), ('quintile-3', 'light gray', 'black'),
    ('quintile-4', 'light gray', 'black'), ('quintile-5', 'white', 'black'),
]

PALETTE = PALETTE_MINIMAL



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
        return str(int(dist)) + Units.M
    else:
        return format_km(dist / 1000)


def format_km(dist):
    return f'{dist:.1f}{Units.KM}'


def format_percent(pc):
    if pc > 0.5:
        return f'{pc:.1f}{Units.PC}'
    else:
        return f'{pc:.2f}{Units.PC}'


def format_watts(power):
    return str(int(power)) + Units.W


def groupby_tuple(iterable, key=None):
    for name, group in groupby(iterable, key=key):
        yield name, tuple(group)


def group_to_dict(iterable):
    'Expects iterable to be (key, value) tuples.'
    d = defaultdict(list)
    for key, value in iterable:
        d[key].append(value)
    return d


def drop_trailing_slash(path):
    left, right = split(path)
    if not right:
        return left
    else:
        return path


def inside_interval(lo, value, hi):
    if lo is None:
        if hi is None:
            return True
        else:
            return value < hi
    else:
        if hi is None:
            return lo <= value
        else:
            return lo <= value < hi


def restart_self():
    # https://stackoverflow.com/questions/11329917/restart-python-script-from-within-itself
    log.info('Shutting down')
    try:
        p = Process(getpid())
        for handler in p.open_files() + p.connections():
            close(handler.fd)
    except Exception as e:
        log.warning(e)
    python = executable
    args = argv
    # weird hack that i don't understand
    args = ['-m', 'ch2'] + args[1:]
    log.info(f'Restarting {python} {args}')
    execl(python, python, *args)
    # no need to exit as we do not return


def clean_path(path):
    return realpath(normpath(expanduser(path)))


def slow_warning(msg, n=3, pause=1):
    for _ in range(3):
        log.warning(msg)
        sleep(pause)


def parse_bool(text, default=False):
    if isinstance(text, bool): return text
    if not text: return default
    ltext = text.strip().lower()
    if ltext in ('y', 't', 'yes', 'true'): return True
    if ltext in ('n', 'f', 'no', 'false'): return False
    if default is None: raise ValueError(f'Cannot parse {text} as a boolean')
    return default


@contextmanager
def timing(label, warn_over=None):
    start = now()
    yield
    seconds = (now() - start).total_seconds()
    if warn_over and seconds > warn_over:
        log.warning(f'{seconds:.1f}s > {warn_over:.1f}s {label}')
    else:
        log.debug(f'{seconds:.1f}s {label}')


def clean(token, none=False):
    if token is None and none:
        return None
    else:
        return token.strip().lower()
