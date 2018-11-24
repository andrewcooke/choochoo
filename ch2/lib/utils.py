
import time as t

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
    return t.mktime(datetime.timetuple())


def interleave(sep, iter):
    for started, value in enumerate(iter):
        if started:
            yield sep
        yield value
