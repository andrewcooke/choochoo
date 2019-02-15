
from inspect import getfullargspec

from .load import display_notebook


def template(func):

    def wrapper(*args, log=None, direct=False, **kargs):
        if direct:
            return func(*args, **kargs)
        else:
            all_args = dict(kargs)
            for name, value in zip(getfullargspec(func).args, args):
                all_args[name] = value
            display_notebook(log, func, **all_args)

    return wrapper
