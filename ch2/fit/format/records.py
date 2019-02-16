
import itertools as it
from collections import namedtuple, OrderedDict

# todo - remove 's' units from timestamps if they are datetime instances
from ...lib.data import dict_to_attr


def no_filter(data):
    return data


def no_bad_values(data):
    for name, (values, units) in data:
        if values is not None:
            yield name, (values, units)


def no_unknown_fields(data):
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


def to_hex(data):
    for name, (values, units) in data:
        if values is None:
            yield name, (values, units)
        else:
            if len(values) > 1:  # single values are best displayed as integers (common data type)
                try:
                    values = ('0x'+values.hex(),)
                except AttributeError:
                    pass
            yield name, (values, units)


def append_units(data, separator=''):
    for name, (values, units) in data:
        if values is None:  # preserve bad values as bad
            yield name, None
        elif units:
            yield name, tuple(str(value) + separator + units for value in values)
        else:
            yield name, tuple(str(value) for value in values)


def join_values(data, separator=','):
    for name, values in data:
        if values is None:
            yield name, values
        else:
            yield name, separator.join(values)


def fix_degrees(data, new_units='°'):
    for name, (values, units) in data:
        if values is not None and units == 'semicircles':
            values = tuple(value * 180 / 2**31 for value in values)
            units = new_units
        yield name, (values, units)


def unpack_single_bytes(data):
    for name, (values, units) in data:
        if values is None or not (isinstance(values, bytes) and len(values) == 1):
            yield name, (values, units)
        else:
            yield name, (values[0], units)


def unique_names(data):
    known = set()
    for name, values_or_pair in data:
        if name not in known:
            yield name, values_or_pair
        known.add(name)


# this is intended for slurping to a dict - it does not (cannot) remove earlier entries,
# but accumulates duplicates in later entries.
def merge_duplicates(data):
    known = {}
    data = list(data)
    for name, (values, units) in data:
        if name in known and known[name][0] is not None:
            values = known[name][0] + values
        known[name] = (values, units)
        yield name, known[name]


def restrict_names(names):
    def filter(data):
        for name, values_or_pair in data:
            if name in names:
                yield name, values_or_pair
    return filter


def chain(*filters):
    def expand(data, filters=filters):
        if filters:
            filter, filters = filters[0], filters[1:]
            return filter(expand(data, filters=filters))
        else:
            return data
    return expand


class Record(namedtuple('BaseRecord', 'name, number, identity, timestamp, data')):

    __slots__ = ()

    def is_known(self):
        return self.name[0].islower()

    def data_with(self, **kargs):
        return it.chain(self.data, kargs.items())

    def into(self, container, *filters, _cls=None, **extras):
        if not _cls:
            _cls = Record
        return _cls(self.name, self.number, self.identity, self.timestamp,
                    container(chain(*filters)(self.data_with(**extras))))

    def as_dict(self, *filters, **extras):
        return self.into(OrderedDict, *filters, **extras, _cls=DictRecord)

    def as_names(self, *filters, **extras):
        return self.into(tuple, *(no_values,)+filters, **extras)

    def as_values(self, *filters, **extras):
        return self.into(tuple, *(no_names,)+filters, **extras)

    def force(self, *filters, **extras):
        if filters or extras:
            return self.into(type(self.data), *filters, **extras)
        else:
            return self


class LazyRecord(Record):

    __slots__ = ()

    def force(self, *filters, **extras):
        return self.as_dict(*filters, **extras)


class Values:

    def __init__(self, attr):
        self.__attr = attr

    def __getattr__(self, name):
        try:
            (values, units) = getattr(self.__attr, name)
            return values[0]
        except:
            if self.__or_none:
                return None
            else:
                raise


class DictRecord(Record):

    def __new__(cls, *args, **kargs):
        self = super().__new__(cls, *args, **kargs)
        self.attr = dict_to_attr(self.data)
        self.value = Values(self.attr)
        return self

    def data_with(self, **kargs):
        return it.chain(self.data.items(), kargs.items())

