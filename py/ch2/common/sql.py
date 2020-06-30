import datetime as dt

from sqlalchemy import TypeDecorator, Integer, Float


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
            # only store 2dp (1/100 second).  trying to get something that matches on equality for float
            # since we retrieve on equality and sqlite doesn't have decimal types
            converted = int(100 * to_time(time).timestamp()) / 100
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
