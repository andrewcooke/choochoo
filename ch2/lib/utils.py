
import time as t


def sign(x):
    if x == 0:
        return 0
    elif x > 0:
        return 1
    else:
        return -1


PALETTE = [('plain', 'light gray', 'black'), ('plain-focus', 'white', 'black'),
           ('em', 'white', 'black'),
           ('label', 'dark gray', 'black'),
           ('selected', 'black', 'light gray'), ('selected-focus', 'black', 'white'),
           ('unimportant', 'dark blue', 'black'), ('unimportant-focus', 'light blue', 'black'),
           ('error', 'dark red', 'black'), ('error-focus', 'light red', 'black'),
           ('bar', 'dark gray', 'black'), ('bar-focus', 'dark gray', 'black'),
           ('rank-1', 'white', 'black'), ('rank-2', 'dark red', 'black'), ('rank-3', 'yellow', 'black'),
           ('rank-4', 'dark green', 'black'), ('rank-5', 'light gray', 'black'),
           ('zone-5', 'black', 'white'), ('zone-4', 'black', 'dark red'), ('zone-3', 'black', 'yellow'),
           ('zone-2', 'black', 'dark green'), ('zone-1', 'black', 'light gray'),
           ('quintile-1', 'light gray', 'black'), ('quintile-2', 'light green', 'black'), ('quintile-3', 'yellow', 'black'),
           ('quintile-4', 'light red', 'black'), ('quintile-5', 'white', 'black'),
           ]


def em(text):
    return 'em', text


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
