
import datetime as dt

from .load import display_notebook
from ..common.date import format_date, time_to_local_time


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

    def wrapper(*args, config=None):
        if config:
            sargs = [stringify(arg) for arg in args]
            display_notebook(config, func, sargs)
        else:
            return func(*args)

    wrapper._original = func

    return wrapper
