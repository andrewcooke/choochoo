
import datetime as dt
from json import dumps, loads
from logging import getLogger
from pydoc import locate

from sqlalchemy import TypeDecorator, Integer, Float, Text

from ..lib.date import to_time, to_date
from ..lib.schedule import Schedule

log = getLogger(__name__)


class Date(TypeDecorator):

    impl = Integer

    def process_literal_param(self, date, dialect):
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


class Str(TypeDecorator):

    impl = Text

    def process_literal_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, int):
            raise Exception('Passing primary key instead of class?')
        return str(value)

    process_bind_param = process_literal_param


class NullStr(TypeDecorator):
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
        if sched is None:
            return sched
        if not isinstance(sched, Schedule):
            sched = Schedule(sched)
        return str(sched)

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Schedule(value)


class OpenSched(Sched):

    def process_literal_param(self, sched, dialect):
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
