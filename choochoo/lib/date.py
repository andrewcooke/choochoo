
import datetime as dt
import time as t


def parse_date(text):
    return dt.date(*t.strptime(text, '%Y-%m-%d')[:3])


def format_date(date):
    return date.strftime('%Y-%m-%d')
