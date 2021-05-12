from json import dumps, loads
from logging import getLogger
from pydoc import locate
from re import compile, IGNORECASE

import pytz
from geoalchemy2 import Geography
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import TypeDecorator, Integer, Text, func, DateTime

from .utils import WGS84_SRID
from ..names import simple_name

log = getLogger(__name__)


CLS_CACHE = {}


class Cls(TypeDecorator):

    impl = Text
    cache_ok = True

    def process_literal_param(self, cls, dialect):
        return long_cls(cls)

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        return lookup_cls(value)


def long_cls(cls):
    if cls is None:
        return cls
    if not isinstance(cls, str) and not isinstance(cls, type):
        cls = type(cls)
    if isinstance(cls, type):
        cls = cls.__module__ + '.' + cls.__name__
    return cls


def lookup_cls(value):
    # https://stackoverflow.com/a/24815361
    if not value:
        return None
    if value not in CLS_CACHE:
        CLS_CACHE[value] = locate(value)
    if not CLS_CACHE[value]:
        raise Exception('Cannot find %s' % value)
    return CLS_CACHE[value]


class ShortCls(TypeDecorator):

    impl = Text
    cache_ok = True

    def process_literal_param(self, cls, dialect):
        return short_cls(cls)

    process_bind_param = process_literal_param


def short_cls(cls):
    if cls is None:
        return cls
    if not isinstance(cls, str) and not isinstance(cls, type):
        cls = type(cls)
    if isinstance(cls, type):
        cls = cls.__name__
    return cls


class NullText(TypeDecorator):
    '''
    None (NULL) values are converted to 'None'.

    Use for constraint, where NULLs are distinct in UNIQUE constraints.
    '''

    impl = Text
    cache_ok = True

    def process_literal_param(self, value, dialect):
        return str(value)

    process_bind_param = process_literal_param

    coerce_to_is_types = tuple()  # don't want "IS NULL" when comparing with None


class Json(TypeDecorator):

    impl = Text
    cache_ok = True

    def process_literal_param(self, value, dialect):
        return dumps(value)

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        return loads(value)


class Sched(TypeDecorator):

    impl = Text
    cache_ok = True

    def process_literal_param(self, sched, dialect):
        from ..lib.schedule import Schedule
        if sched is None:
            return sched
        if not isinstance(sched, Schedule):
            sched = Schedule(sched)
        return str(sched)

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        from ..lib.schedule import Schedule
        if value is None:
            return None
        return Schedule(value)


class OpenSched(Sched):

    cache_ok = True

    def process_literal_param(self, sched, dialect):
        from ..lib.schedule import Schedule
        if sched is None:
            return sched
        if not isinstance(sched, Schedule):
            sched = Schedule(sched)
        sched.start = None
        sched.finish = None
        return str(sched)

    process_bind_param = process_literal_param


class Sort(TypeDecorator):

    impl = Integer
    cache_ok = True

    def process_literal_param(self, value, dialect):
        if callable(value):
            value = value()
        return value

    process_bind_param = process_literal_param


class Name(TypeDecorator):

    impl = Text
    cache_ok = True

    def process_literal_param(self, value, dialect):
        return simple_name(value)

    process_bind_param = process_literal_param


class QualifiedName(TypeDecorator):

    impl = Text
    cache_ok = True

    def process_literal_param(self, value, dialect):
        if value and ':' in value:
            left, right = value.rsplit(':', 1)
            return simple_name(left) + ':' + simple_name(right)
        else:
            return simple_name(value)

    process_bind_param = process_literal_param


def point(x, y, srid=-1):
    # return from_shape(Point(x, y), srid=srid)
    return f'ST_MakePoint({x}, {y})'


def linestringxyzm(xyzm, type='geography'):
    if xyzm:
        points = [f'ST_MakePoint({x}, {y}, {z}, {m})' for x, y, z, m in xyzm]
        line = f'ST_MakeLine(ARRAY[{", ".join(points)}])'
    else:
        log.warning(f'Empty geo data')
        line = "'LINESTRINGZM EMPTY'::" + type
    return line


def linestringxym(xym, type='geography'):
    if xym:
        points = [f'ST_MakePointM({x}, {y}, {m})' for x, y, m in xym]
        line = f'ST_MakeLine(ARRAY[{", ".join(points)}])'
    else:
        log.warning(f'Empty geo data')
        line = "'LINESTRINGM EMPTY'::" + type
    return line


def linestringxyz(xyz, type='geography'):
    if xyz:
        points = [f'ST_MakePoint({x}, {y}, {z})' for x, y, z in xyz]
        line = f'ST_MakeLine(ARRAY[{", ".join(points)}])'
    else:
        log.warning(f'Empty geo data')
        line = "'LINESTRINGZ EMPTY'::" + type
    return line


def linestringxy(xy, type='geography'):
    if xy:
        points = [f'ST_MakePoint({x}, {y})' for x, y in xy]
        line = f'ST_MakeLine(ARRAY[{", ".join(points)}])'
    else:
        log.warning(f'Empty geo data')
        line = "'LINESTRING EMPTY'::" + type
    return line


NAME = 'name'
TITLE = 'title'
OWNER = 'owner'


def name_and_title(kargs):
    '''
    allow one or the other to be specified, with special treatment for name only to support legacy code.
    '''

    def add_owner(msg):
        if OWNER in kargs: msg += f' (owner {short_cls(kargs[OWNER])})'
        return msg

    if kargs.get(NAME, None):  # not missing and not None
        name = kargs[NAME]
        if not kargs.get(TITLE, None):
            kargs[TITLE] = name
            log.warning(add_owner(f'Setting title from name "{name}"'))
            kargs[NAME] = simple_name(name)
        else:
            if kargs[NAME] != simple_name(name):
                log.warning(add_owner(f'Unusual name ({name}) for title ({kargs[TITLE]})'))
    elif kargs.get(TITLE, None):
        log.debug(f'Setting name from title ({kargs[TITLE]})')
        kargs[NAME] = simple_name(kargs[TITLE])
    else:
        raise Exception(f'Provide {NAME} or {TITLE}')
    return kargs


class UTC(TypeDecorator):

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=pytz.UTC)
