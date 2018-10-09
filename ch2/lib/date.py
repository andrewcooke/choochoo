
import datetime as dt
import time as t
from calendar import monthrange


def format_date(date):
    return date.strftime('%Y-%m-%d')


def format_time(datetime):
    return datetime.strftime('%H:%M:%S')


def format_datetime(datetime):
    return datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')


def parse_duration(duration):
    try:
        return int(duration), 'm'
    except ValueError:
        return int(duration[:-1]), duration[-1]


def to_date(value, none=False):
    if none and value is None:
        return None
    if isinstance(value, dt.datetime):
        return dt.date(value.year, value.month, value.day)
    elif isinstance(value, dt.date):
        return value
    elif isinstance(value, int):
        return dt.date.fromordinal(value)
    else:
        return dt.date(*t.strptime(value, '%Y-%m-%d')[:3])


def to_datetime(value, none=False):
    if none and value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    elif isinstance(value, dt.date):
        return dt.datetime(value.year, value.month, value.day)
    elif isinstance(value, int):
        return dt.datetime.fromtimestamp(value, dt.timezone.utc)
    elif isinstance(value, float):
        return dt.datetime.fromtimestamp(value, dt.timezone.utc)
    else:
        for format in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d'):
            try:
                return dt.datetime.strptime(value, format)
            except ValueError:
                pass
        raise ValueError('Cannot parse "%s" as a datetime' % value)


# these reflect the conventions used in string parsing / formatting
# schedules are for longer intervals (>= 1d) and so can be case-agnostic.
SECOND = 's'
MINUTE = 'm'
HOUR = 'h'
DAY = 'd'
WEEK = 'w'
MONTH = 'M'
YEAR = 'y'


def add_duration(date, duration):
    (n, unit) = duration
    if unit == DAY:
        return date + dt.timedelta(days=n)
    if unit == WEEK:
        return date + dt.timedelta(days=n*7)
    if unit == MONTH:
        year, month = date.year, date.month + n
        while month > 12:
            month -= 12
            year += 1
        return dt.date(year, month, min(date.day, monthrange(year, month)[1]))
    if unit == YEAR:
        year = date.year + n
        return dt.date(year, date.month, min(date.day, monthrange(year, date.month)[1]))
    raise Exception('Unexpected unit "%s" (need one of d, w, M, y)' % unit)


def mul_duration(n, duration):
    return n * duration[0], duration[1]


def duration_to_secs(duration):
    (n, unit) = duration
    if unit == SECOND:
        return n
    if unit == MINUTE:
        return n * 60
    if unit == HOUR:
        return n * 60 * 60
    if unit == DAY:
        return n * 24 * 60 * 60
    if unit == WEEK:
        return n * 7 * 24 * 60 * 60
    raise Exception('Unexpected unit "%s" (need one of s, m, h, d, w' % unit)


def format_duration(seconds):
    if seconds >= 60:
        minutes, seconds = seconds // 60, seconds % 60
        if minutes >= 60:
            hours, minutes = minutes // 60, minutes % 60
            return '%dh%02dm%02ds' % (hours, minutes, seconds)
        else:
            return '%dm%02ds' % (minutes, seconds)
    else:
        return '%ds' % seconds
