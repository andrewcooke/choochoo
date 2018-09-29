
import datetime as dt
import time as t
from calendar import monthrange


def parse_date(text):
    return dt.date(*t.strptime(text, '%Y-%m-%d')[:3])


def parse_datetime(text):
    for format in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d'):
        try:
            return dt.datetime.strptime(text, format)
        except ValueError:
            pass
    raise ValueError('Cannot parse "%s" as a datetime' % text)


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


def to_date(datetime):
    return dt.date(datetime.year, datetime.month, datetime.day)


def to_datetime(date):
    return dt.datetime(date.yeat, date.month, date.day)


def add_duration(date, duration):
    (n, unit) = duration
    if unit == 'd':
        return date + dt.timedelta(days=n)
    if unit == 'w':
        return date + dt.timedelta(days=n*7)
    if unit == 'M':
        year, month = date.year, date.month + n
        while month > 12:
            month -= 12
            year += 1
        return dt.date(year, month, min(date.day, monthrange(year, month)[1]))
    if unit == 'y':
        year = date.year + n
        return dt.date(year, date.month, min(date.day, monthrange(year, date.month)[1]))
    raise Exception('Unexpected unit "%s" (need one of d, w, M, y)' % unit)


def duration_to_secs(duration):
    (n, unit) = duration
    if unit == 's':
        return n
    if unit == 'm':
        return n * 60
    if unit == "h":
        return n * 60 * 60
    if unit == 'd':
        return n * 24 * 60 * 60
    if unit == 'w':
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
