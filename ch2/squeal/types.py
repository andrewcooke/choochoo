
import datetime as dt
from hashlib import md5
from json import dumps, loads
from pydoc import locate
from struct import unpack

from sqlalchemy import TypeDecorator, Integer, Float, Text

from ..lib.date import to_time, to_date
from ..lib.schedule import Schedule


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
            return to_time(time).timestamp()

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return dt.datetime.fromtimestamp(value, dt.timezone.utc)


CLS_CACHE = {}


class Cls(TypeDecorator):

    impl = Text

    def process_literal_param(self, cls, dialect):
        if cls is None:
            return cls
        if not isinstance(cls, str) and not isinstance(cls, type):
            cls = type(cls)
        if isinstance(cls, type):
            cls = cls.__module__ + '.' + cls.__name__
        return cls

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        # https://stackoverflow.com/a/24815361
        if not value:
            return None
        if value not in CLS_CACHE:
            CLS_CACHE[value] = locate(value)
        if not CLS_CACHE[value]:
            raise Exception('Cannot find %s' % value)
        return CLS_CACHE[value]


class Json(TypeDecorator):

    impl = Text

    def process_literal_param(self, value, dialect):
        return dumps(value)

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        return loads(value)


class Owner(TypeDecorator):
    '''
    The 'owner' of some data - typically the creating class.
    We used to store the whole class name, but that was long text and seemed ot be a
    waste of space.  Since it's an opaque value we now use a 32bit hash.
    '''

    impl = Integer

    def process_literal_param(self, cls, dialect):
        if cls is None or isinstance(cls, int):
            return cls
        raise Exception('Use intern(...) for Owner')

    process_bind_param = process_literal_param


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
