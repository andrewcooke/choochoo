
from binascii import hexlify
from collections import namedtuple
from inspect import stack, getmodule
from json import loads


class WarnDict(dict):

    def __init__(self, log, msg):
        self.__log = log
        self.__msg = msg
        super().__init__()

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            msg = self.__msg % (item,)
            self.__log.debug(msg)
            raise KeyError(msg)


class WarnList(list):

    def __init__(self, log, msg):
        self.__log = log
        self.__msg = msg
        super().__init__()

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except IndexError:
            msg = self.__msg % item
            self.__log.debug(msg)
            raise IndexError(msg)


def tohex(data):
    return hexlify(data).decode('ascii')


def assert_attr(instance, *attrs):
    for attr in attrs:
        if getattr(instance, attr) is None:
            raise Exception('No %s defined' % attr)


def kargs_to_attr(**kargs):
    return dict_to_attr(kargs)


def dict_to_attr(kargs):
    return namedtuple('Attr', kargs.keys(), rename=True)(*kargs.values())


class MutableAttr(dict):

    def __init__(self, *args, none=False, **kargs):
        self.__none = none
        super().__init__(*args, **kargs)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            if self.__none:
                return None
            else:
                raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self[name] = value

    def _to_dict(self):
        return self.__dict__


class MissingReference(Exception): pass


def reftuple(name, *args, **kargs):
    '''
    Like a namedtuple, but expands $ strings using a database session and date
    (# is similar, but also does JSON parsing).
    '''

    from ..squeal import StatisticJournal, StatisticName

    class klass(namedtuple(name, *args, **kargs)):

        def expand(self, log, s, time, owner=None, constraint=None):
            instance = self
            for name in self._fields:
                value = getattr(instance, name)
                if isinstance(value, str) and len(value) > 0 and value[0] in '$#':
                    log.info(f'Expanding {value} for {name}')
                    replacement = self._lookup(log, s, time, value[1:], value[0] == '#',
                                               default_value=self._fields_defaults.get(name, None),
                                               default_owner=owner, default_constraint=constraint)
                    instance = instance._replace(**{name: replacement})
            return instance

        def _lookup(self, log, s, time, name, json,
                    default_value=None, default_owner=None, default_constraint=None):
            if isinstance(name, str) and len(name) > 0 and name[0] in '$#':
                name = self._lookup(log, s, time, name[1:], name[0] == '#',
                                    default_owner=default_owner, default_constraint=default_constraint)
            owner, name, constraint = StatisticName.parse(name, default_owner=default_owner,
                                                          default_constraint=default_constraint)
            value = StatisticJournal.before(s, time, name, owner, constraint)
            if value is None:
                if default_value:
                    log.warning(f'No value found for {owner}:{name}:{constraint} (default {default_value})')
                    value = default_value
                else:
                    raise MissingReference(f'No value found for {owner}:{name}:{constraint} (and no default)')
            else:
                value = value.value
                if json:
                    log.debug(f'Unpacking JSON "{value}"')
                    value = loads(value)
                log.info(f'{name} -> {value}')
            return value

    klass.__name__ = name
    caller = stack()[1]
    klass.__module__ = getmodule(None, caller.filename).__name__
    return klass


class MaxDict(dict):

    def __init__(self, kv):
        super().__init__()
        for key, value in kv:
            if key in self:
                self[key] = max(value, self[key])
            else:
                self[key] = value


def nearest_index(df, name, value):
    exactmatch = df.loc[df[name] == value]
    if not exactmatch.empty:
        return exactmatch.index[0]
    else:
        lower = df.loc[df[name] < value].index.dropna()
        upper = df.loc[df[name] > value].index.dropna()
        if lower.empty:
            return upper.min()
        elif upper.empty:
            return lower.max()
        else:
            if abs(value - df.loc[lower.max()][name]) < abs(value - df.loc[upper.min()][name]):
                return lower.max()
            else:
                return upper.min()


def get_index_loc(df, value):
    loc = df.index.get_loc(value)
    try:
        return loc.start  # if slice, take first
    except AttributeError:
        return loc  # otherwise, simple value
