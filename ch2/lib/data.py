
from collections import namedtuple
from inspect import stack, getmodule
from json import loads
from logging import getLogger
from random import choice
from re import sub, compile
from string import ascii_letters

import pandas as pd
from binascii import hexlify

from ..stats.names import BOOKMARK

log = getLogger(__name__)


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

    class klass(namedtuple(name, *args, **kargs)):

        def expand(self, s, time, default_owner=None, default_constraint=None):
            instance = self
            for name in self._fields:
                value = expand(s, getattr(instance, name), time,
                               default_owner=default_owner, default_constraint=default_constraint)
                instance = instance._replace(**{name: value})
            return instance

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


def tmp_name():
    return ''.join(choice(ascii_letters) for _ in range(8))


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


def linscale(series, lo=0, hi=None, min=0, max=1, gamma=1):
    lo = series.dropna().min() if lo is None else lo
    hi = series.dropna().max() if hi is None else hi
    return (min + (max - min) * ((series - lo) / (hi - lo)) ** gamma).clip(min, max)


def sorted_numeric_labels(labels, text=None):
    if text:
        labels = [label for label in labels if text in label]
    return sorted(labels, key=lambda label: int(sub(r'\D', '', label)))


def interpolate_freq(df, freq, **kargs):
    left = pd.DataFrame(index=pd.date_range(df.index.min(), df.index.max(), freq=freq))
    return left_interpolate(left, df, **kargs)


def left_interpolate(left, right, **kargs):
    '''
    interpolate right so that it is on the same index as left.
    '''
    # neater solution https://stackoverflow.com/questions/47148446/pandas-resample-interpolate-is-producing-nans
    # option 1 with reindexing
    tmp = tmp_name()
    left[tmp] = True
    both = left.join(right, how='outer').interpolate(**kargs)
    return both.loc[both[tmp] == True].drop(columns=[tmp])


def bookend(df, column=BOOKMARK):
    # https://stackoverflow.com/questions/53927414/get-only-the-first-and-last-rows-of-each-group-with-pandas
    g = df.groupby(column)
    return pd.concat([g.head(1), g.tail(1)]).drop_duplicates().sort_index()


def expand(s, text, before, vars=None, default_owner=None, default_constraint=None):
    '''
    Recursively expand any ${name} occurrences in the text using vars (if given) and database.

    May be too much magic going on here - can return objects, values as well as strings.
    '''

    from ..sql import StatisticName, StatisticJournal

    if vars is None: vars = {}
    pattern = compile(r'(.*)\${([^}]+)}(.*)')

    match = pattern.match(text)
    while match:
        left, name, right = match.groups()
        if name in vars:
            owner = None
            value = vars[name]
        else:
            owner, statistic, constraint = StatisticName.parse(name, default_owner=default_owner,
                                                               default_constraint=default_constraint)
            value = StatisticJournal.before_not_null(s, before, statistic, owner, constraint)
        if value is None:
            raise Exception(f'No value defined for {name} ({owner}:{statistic}:{constraint}) before {before}')
        elif left == '' and right == '':
            text = value.value
            match = None
            if owner == 'Constant':
                text = loads(text)
            log.debug(f'Unpacked {name}={text}')
        else:
            value = str(value.value)
            log.debug(f'Substituting {name}="{value}" in "{text}"')
            text = left + value + right
            match = pattern.match(text)
    return text


def median(list):
    if not list: raise ValueError('Median of empty set')
    list = sorted(list)
    n = len(list)
    if n % 2:
        return list[n//2]
    else:
        return list[n//2] + list[n//2+1]
