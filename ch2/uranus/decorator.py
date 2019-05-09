
import datetime as dt

from .load import display_notebook
from ..lib.date import format_date, time_to_local_time


def stringify(value):
    if isinstance(value, str):
        return value
    elif isinstance(value, dt.datetime):
        return time_to_local_time(value)
    elif isinstance(value, dt.date):
        return format_date(value)
    else:
        return str(value)


def template(func):

    def wrapper(*args, direct=False, local=True, **kargs):
        if direct:
            return func(*args, **kargs)
        else:
            sargs = [stringify(arg) for arg in args]
            skargs = dict((name, stringify(value)) for name, value in kargs.items())
            display_notebook(func, sargs, skargs, local=local)

    wrapper._original = func

    return wrapper
