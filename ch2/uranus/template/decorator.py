
import datetime as dt
from inspect import getfullargspec

from ch2.lib.date import format_time, format_date
from .load import display_notebook


def stringify(value):
    if isinstance(value, str):
        return value
    elif isinstance(value, dt.datetime):
        return format_time(value)
    elif isinstance(value, dt.date):
        return format_date(value)
    else:
        return str(value)


def template(func):

    def wrapper(*args, log=None, direct=False, **kargs):
        if direct:
            return func(*args, **kargs)
        else:
            sargs = [stringify(arg) for arg in args]
            skargs = dict((name, stringify(value)) for name, value in kargs.items())
            display_notebook(log, func, sargs, skargs)
    return wrapper
