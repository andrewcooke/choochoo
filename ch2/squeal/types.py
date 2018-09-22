
import datetime as dt

from sqlalchemy import TypeDecorator, Integer, Float

from ch2.lib.date import parse_datetime, parse_date


class Ordinal(TypeDecorator):

    impl = Integer

    def process_literal_param(self, date, dialect):
        if date is None:
            return date
        if isinstance(date, str):
            date = parse_date(date)
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
        if isinstance(datetime, str):
            datetime = parse_datetime(datetime)
        return datetime.replace(tzinfo=dt.timezone.utc).timestamp()

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return dt.datetime.utcfromtimestamp(value)
