
from sqlalchemy import inspect

from ..lib.data import dict_to_attr


def tables(*classes):
    return dict_to_attr(dict((cls.__name__, inspect(cls).local_table) for cls in classes))


def add(s, instance):
    s.add(instance)
    return instance
