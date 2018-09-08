
import time as t


def sign(x):
    if x == 0:
        return 0
    elif x > 0:
        return 1
    else:
        return -1


PALETTE = [('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
           ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
           ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black'),
           ('error', 'dark red', 'black'), ('error-focus', 'light red', 'black'),
           ('bar', 'dark gray', 'black'), ('bar-focus', 'dark gray', 'black'),
           ('rank-1', 'black', 'red'),  ('rank-2', 'black', 'yellow'),  ('rank-3', 'black', 'green'),
           ]


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
