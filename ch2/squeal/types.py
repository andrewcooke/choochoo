
import datetime as dt

from sqlalchemy import TypeDecorator, Integer


class Ordinal(TypeDecorator):

    impl = Integer

    def process_literal_param(self, date, dialect):
        if date is None:
            return date
        else:
            return date.toordinal()

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return dt.date.fromordinal(value)
