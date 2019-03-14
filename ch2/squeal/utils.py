
from sqlalchemy import inspect

from ..lib.data import dict_to_attr


class ORMUtils:

    def _get_or_create(self, session, cls, **kargs):
        query = session.query(cls)
        for (name, value) in kargs.items():
            query = query.filter(getattr(cls, name) == value)
        instance = query.one_or_none()
        if instance is None:
            instance = cls(**kargs)
            session.add(instance)
        return instance


def tables(*classes):
    return dict_to_attr(dict((cls.__name__, inspect(cls).local_table) for cls in classes))


def add(s, instance):
    s.add(instance)
    return instance
