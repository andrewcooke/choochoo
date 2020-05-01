
from collections import namedtuple
from logging import getLogger

log = getLogger(__name__)


def make_waypoint(names, extra=None):
    names = list(names)
    if extra:
        names += [extra]
    names = ['time'] + names
    defaults = [None] * len(names)
    return namedtuple('Waypoint', names, defaults=defaults)


def filter_none(names, waypoints):
    names = list(names)
    return [w for w in waypoints if all(n in w._fields and getattr(w, n) is not None for n in names)]
