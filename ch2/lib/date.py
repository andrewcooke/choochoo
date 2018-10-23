
import pendulum as p
import datetime as dt
import time as t
from calendar import monthrange


def format_date(date):
    return date.strftime('%Y-%m-%d')


def format_time(time):
    return time.strftime('%Y-%m-%dT%H:%M:%S.%f')


def to_date(value, none=False):
    if none and value is None:
        return None
    if isinstance(value, dt.datetime):
        raise Exception('Use tz-aware conversion')
    elif isinstance(value, dt.date):
        return value
    elif isinstance(value, int):
        return dt.date.fromordinal(value)
    else:
        return dt.date(*t.strptime(value, '%Y-%m-%d')[:3])


def to_time(value, none=False):
    if none and value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.replace(tzinfo=dt.timezone.utc)
    elif isinstance(value, dt.date):
        raise Exception('Use tz-aware conversion')
    elif isinstance(value, int):
        return to_time(to_date(value))
    elif isinstance(value, float):
        return dt.datetime.fromtimestamp(value, dt.timezone.utc)
    else:
        for format in ('%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S.%f',
                       '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S',
                       '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
            try:
                return dt.datetime.strptime(value, format).replace(tzinfo=dt.timezone.utc)
            except ValueError:
                pass
        raise ValueError('Cannot parse "%s" as a datetime' % value)


DAY = 'd'
WEEK = 'w'
MONTH = 'm'
YEAR = 'y'


def add_date(date, duration):
    # this only works with dates
    # before, working with datetime, we had confusion between dates and datetimes and unnecessary conversions
    # now, for times, use timedelta.
    date, n, unit = to_date(date), duration[0], duration[1].lower()
    if unit == DAY:
        return date + dt.timedelta(days=n)
    if unit == WEEK:
        return date + dt.timedelta(days=n * 7)
    if unit == MONTH:
        year, month = date.year, date.month + n
        while month > 12:
            month -= 12
            year += 1
        while month < 1:
            month += 12
            year -= 1
        return dt.date(year, month, min(date.day, monthrange(year, month)[1]))
    if unit == YEAR:
        year = date.year + n
        return dt.date(year, date.month, min(date.day, monthrange(year, date.month)[1]))
    raise Exception('Unexpected unit "%s" (need one of %s, %s, %s, %s)' % (unit, DAY, WEEK, MONTH, YEAR))


def format_seconds(seconds):
    if seconds >= 60:
        minutes, seconds = seconds // 60, seconds % 60
        if minutes >= 60:
            hours, minutes = minutes // 60, minutes % 60
            return '%dh%02dm%02ds' % (hours, minutes, seconds)
        else:
            return '%dm%02ds' % (minutes, seconds)
    else:
        return '%ds' % seconds


def local_date_to_time(date):
    ptime = p.DateTime(year=date.year, month=date.month, day=date.day,
                       tzinfo=p.tz.get_local_timezone()).in_timezone(dt.timezone.utc)
    return dt.datetime(*ptime.timetuple()[:6], tzinfo=dt.timezone.utc)


def time_to_local_date(time):
    ptime = p.DateTime(*time.timetuple()[:6], tzinfo=dt.timezone.utc).in_timezone(p.tz.get_local_timezone())
    return dt.date(year=ptime.year, month=ptime.month, day=ptime.day)
