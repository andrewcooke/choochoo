
import datetime as dt

from .load import display_notebook
from ..lib.date import format_date, time_to_local_time


def stringify(value):
    # this has auto-conversion of UTC to local times (since interface is public)
    if isinstance(value, str):
        return value
    elif isinstance(value, dt.datetime):
        return time_to_local_time(value)
    elif isinstance(value, dt.date):
        return format_date(value)
    else:
        return str(value)


def template(func):

    def wrapper(*args, direct=False, **kargs):
        if direct:
            return func(*args, **kargs)
        else:
            sargs = [stringify(arg) for arg in args]
            skargs = dict((name, stringify(value)) for name, value in kargs.items())
            display_notebook(func, sargs, skargs)

    wrapper._original = func
    wrapper.__name__ = func.__name__

    return wrapper
