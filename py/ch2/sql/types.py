
import datetime as dt
from json import dumps, loads
from logging import getLogger
from pydoc import locate
from re import sub

from sqlalchemy import TypeDecorator, Integer, Float, Text

log = getLogger(__name__)


class Date(TypeDecorator):

    impl = Integer

    def process_literal_param(self, date, dialect):
        from ..lib.date import to_date
        if date is None:
            return date
        return to_date(date).toordinal()

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if value < 1:  # bootstrap TopicJournal.date where we set values to 0
            return None
        else:
            return dt.date.fromordinal(value)


class Time(TypeDecorator):

    impl = Float

    def process_literal_param(self, time, dialect):
        from ..lib.date import to_time
        if time is None:
            return time
        else:
            converted = to_time(time).timestamp()
            # log.debug(f'Time (writing): converted {time} to {converted}')
            return converted

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            converted = dt.datetime.fromtimestamp(value, dt.timezone.utc)
            # log.debug(f'Time (reading): converted {value} to {converted}')
            return converted


CLS_CACHE = {}


class Cls(TypeDecorator):

    impl = Text

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

    def process_literal_param(self, value, dialect):
        return str(value)

    process_bind_param = process_literal_param

    coerce_to_is_types = tuple()  # don't want "IS NULL" when comparing with None


class Json(TypeDecorator):

    impl = Text

    def process_literal_param(self, value, dialect):
        return dumps(value)

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        return loads(value)


class Sched(TypeDecorator):

    impl = Text

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

    def process_literal_param(self, value, dialect):
        if callable(value):
            value = value()
        return value

    process_bind_param = process_literal_param


def simple_name(name, none=True, strip=True):
    # allows % and ? for LIKE and templates
    # also allows ':' so that we don't mess up composites
    from ch2.names import POW_2, POW_M1
    if name is None and none:
        return None
    name = name.replace(POW_2, '2')
    name = name.replace(POW_M1, '')  # ms^-1 -> ms which is standard convention
    name = name.replace('Δ', 'd_')
    if strip: name = name.strip()
    name = name.lower()
    name = sub(r'\s+', '_', name)
    name = sub(r'[^a-z0-9%?:]', '_', name)
    name = sub(r'^(\d)', r'_\1', name)
    name = sub(r'_+', '_', name)
    return name


class Name(TypeDecorator):

    impl = Text

    def process_literal_param(self, value, dialect):
        return simple_name(value)

    process_bind_param = process_literal_param


class QualifiedName(TypeDecorator):

    impl = Text

    def process_literal_param(self, value, dialect):
        if value and ':' in value:
            left, right = value.rsplit(':', 1)
            return simple_name(left) + ':' + simple_name(right)
        else:
            return simple_name(value)

    process_bind_param = process_literal_param


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
