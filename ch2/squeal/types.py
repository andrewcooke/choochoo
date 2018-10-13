
import datetime as dt
from json import dumps, loads
from pydoc import locate

from sqlalchemy import TypeDecorator, Integer, Float, Text

from ..lib.schedule import Schedule
from ..lib.date import to_datetime, to_date


class Ordinal(TypeDecorator):

    impl = Integer

    def process_literal_param(self, date, dialect):
        if date is None:
            return date
        if isinstance(date, str):
            date = to_date(date)
        return date.toordinal()

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return dt.date.fromordinal(value)


class Epoch(TypeDecorator):

    impl = Float

    def process_literal_param(self, datetime, dialect):
        if datetime is None:
            return datetime
        else:
            return self.to_time(datetime).replace(tzinfo=dt.timezone.utc).timestamp()

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return dt.datetime.utcfromtimestamp(value)

    @staticmethod
    def to_time(datetime):
        if datetime is None:
            return None
        if isinstance(datetime, str):
            datetime = to_datetime(datetime)
        elif isinstance(datetime, dt.date):
            datetime = dt.datetime.combine(datetime, dt.time())
        elif isinstance(datetime, int) or isinstance(datetime, float):
            datetime = dt.datetime.utcfromtimestamp(datetime)
        return datetime


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
        return CLS_CACHE[value]


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
        if not value:
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
