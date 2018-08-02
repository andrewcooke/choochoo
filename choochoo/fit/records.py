
import itertools as it
from collections import namedtuple


def no_filter(data):
    return data


def no_bad_values(data):
    for name, (values, units) in data:
        if values is not None:
            yield name, (values, units)


def no_unknown(data):
    for name, values_or_pair in data:
        if name[0].islower():
            yield name, values_or_pair


def no_names(data):
    for name, values_or_pair in data:
        yield values_or_pair


def no_values(data):
    for name, values_or_pair in data:
        yield name


def no_units(data):
    for name, (values, units) in data:
        if values is not None:
            yield name, values


def append_units(data, separator=''):
    for name, (values, units) in data:
        if values is None:  # preserve bad values as bad
            yield name, None
        elif units:
            yield name, tuple(str(value) + separator + units for value in values)
        else:
            yield name, tuple(str(value) for value in values)


def join_values(data, separator='.'):
    for name, values in data:
        if values is None:
            yield name, values
        else:
            yield name, separator.join(values)


def fix_degrees(data, new_units='°'):
    for name, (values, units) in data:
        if units == 'semicircles':
            values = tuple(value * 180 / 2**31 for value in values)
            units = new_units
        yield name, (values, units)


def unique_names(data):
    known = set()
    for name, values_or_pair in data:
        if name not in known:
            yield name, values_or_pair
        known.add(name)


def chain(*filters):
    def expand(data, filters=filters):
        filter, filters = filters[0], filters[1:]
        if filters:
            return filter(expand(data, filters=filters))
        else:
            return filter(data)
    return expand


class Record(namedtuple('BaseRecord', 'name, number, identity, timestamp, data')):

    __slots__ = ()

    def is_known(self):
        return self.name[0].islower()

    def data_with(self, *args, **kargs):
        return it.chain(self.data, args, kargs.items())

    def into(self, container, filter=no_filter, extra=None):
        kargs, args = {}, ()
        if extra:
            if isinstance(extra, dict):
                kargs = extra
            else:
                args = extra
        return Record(self.name, self.number, self.identity, self.timestamp,
                      container(filter(self.data_with(*args, **kargs))))

    def as_dict(self, filter=no_filter, extra=None):
        return self.into(dict, filter=filter, extra=extra)

    def as_names(self, filter=no_filter, extra=None):
        return self.into(tuple, filter=chain(no_values, filter), extra=extra)

    def as_values(self, filter=no_filter, extra=None):
        return self.into(tuple, filter=chain(no_names, filter), extra=extra)


class LazyRecord(Record):

    def force(self, filter=no_filter, extra=None):
        return self.into(list, filter=filter, extra=extra)
