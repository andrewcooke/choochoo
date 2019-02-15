
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
            all_args = dict(kargs)
            for name, value in zip(getfullargspec(func).args, args):
                all_args[name] = stringify(value)
            display_notebook(log, func, **all_args)

    return wrapper
