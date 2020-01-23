
from collections import namedtuple
from itertools import repeat, zip_longest

from .support import Named
from ...lib.data import WarnDict

TIMESTAMP_GLOBAL_TYPE = 253


class ScaledField(Named):

    def __init__(self, log, name, units, scale, offset, accumulate):
        super().__init__(log, name)
        self._units = units
        self._scale = scale if scale else 1  # treat 0 as 1
        self._offset = offset if offset else 0
        self._accumulate = accumulate

    def _parse_and_scale(self, type, data, count, endian, timestamp,
                         scale=None, offset=None, accumulators=None, n_bits=None, **options):
        if scale is None: scale = self._scale if self._scale else 1
        if offset is None: offset = self._offset
        values = type.parse_type(data, count, endian, timestamp, scale=scale, offset=offset,
                                 name=self.name, accumulators=accumulators, n_bits=n_bits, **options)
        yield self.name, (values, self._units)

    def register_accumulator(self, accumulators):
        if self._accumulate and self.name not in accumulators:
            accumulators[self.name] = None

    def post(self, message, types):
        '''
        Called after message creation.
        '''
        pass


class TypedField(ScaledField):

    def __init__(self, log, name, field_no, units, scale, offset, accumulate, field_type, types):
        super().__init__(log, name, units, scale, offset, accumulate)
        self.number = field_no
        if name in types.overrides:
            self._log.info('Overriding type for %s (not %s)' % (name, field_type))
            field_type = name
        self.type = types.profile_to_type(field_type)

    def parse_field(self, data, count, endian, timestamp, references, message, **options):
        yield from self._parse_and_scale(self.type, data, count, endian, timestamp, **options)


class RowField(TypedField):

    def __init__(self, log, row, types):
        super().__init__(log, row.field_name, row.single_int(log, row.field_no), row.units,
                         row.single_int(log, row.scale), row.single_int(log, row.offset),
                         row.single_int(log, row.accumulate), row.field_type, types)


class DelegateField(ScaledField):

    def parse_field(self, data, count, endian, timestamp, references, message,
                    scale=None, offset=None, **options):
        scale = self._scale if scale is None else scale
        offset = self._offset if offset is None else offset
        delegate = message.profile_to_field(self.name)
        yield from delegate.parse_field(data, count, endian, timestamp, references, message,
                                        scale=scale, offset=offset, **options)

    def size(self, message):
        # this is needed because we delegate above
        delegate = message.profile_to_field(self.name)
        return delegate.type.n_bytes


class Zip:

    def _zip(self, *fields):
        return zip_longest(*(self.__split(field) for field in fields))

    def __split(self, field):
        if field:
            for value in str(field).split(','):
                yield value.strip()
        else:
            yield None


class CompositeField(Zip, TypedField):

    def __init__(self, log, row, types):
        super().__init__(log, row.field_name, row.single_int(log, row.field_no),
                         None, None, None, None, row.field_type, types)
        self.number = row.single_int(log, row.field_no)
        self._components = []
        self.references = []
        for (name, bits, units, scale, offset, accumulate) in \
                self._zip(row.components, row.bits, row.units, row.scale, row.offset, row.accumulate):
            self._components.append((int(bits),
                                     # set scale / offset below because they seem to override delegate
                                     # (see intensity in CSV examples in SDK inside current_activity_type_intensity)
                                     DelegateField(log, name, units,
                                                    1 if scale is None else float(scale),
                                                    0 if offset is None else float(offset),
                                                    None if accumulate is None else int(accumulate))))
            self.references.append(name)

    def register_accumulator(self, accumulators):
        for _, field in self._components:
            field.register_accumulator(accumulators)

    def parse_field(self, data, count, endian, timestamp, references, message,
                    rtn_composite=False, check_bad=True, n_bits=None, **options):
        if check_bad and self.type.is_bad(data, count, endian):
            yield self.name, (None, self._units)
        else:
            if rtn_composite:  # extra shit for CSV comparison
                yield (self.name, (('COMPOSITE',), self._units))
            byteorder = ['little', 'big'][endian]
            bits = int.from_bytes(data, byteorder=byteorder)
            for n_bits, field in self._components:
                # todo - error if larger
                n_bytes = max((n_bits+7) // 8, field.size(message))
                data = (bits & ((1 << n_bits) - 1)).to_bytes(n_bytes, byteorder=byteorder)
                bits >>= n_bits
                yield from field.parse_field(data, 1, endian, timestamp, references, message,
                                             rtn_composite=rtn_composite, check_bad=False, n_bits=n_bits,
                                             **options)


class DynamicField(Zip, RowField):

    def __init__(self, log, row, rows, types):
        super().__init__(log, row, types)
        self.__dynamic_lookup = WarnDict(log, 'No dynamic field for %r')
        self.references = []
        for row in rows.lookahead():
            if row and row.field_name and row.field_no is None:
                for name, value in self._zip(row.ref_name, row.ref_value):
                    # need to use a list (not set) to preserve order
                    # (and consistently disambiguate multiple matches)
                    if name not in self.references:
                        self.references.append(name)
                    self.__dynamic_lookup[(name, value)] = row.field_name
            else:
                break

    def post(self, message, types):
        # fill in values for when mapping is not used
        for (name, value), field in list(self.__dynamic_lookup.items()):
            value = types.profile_to_type(message.profile_to_field(name).type.name).profile_to_internal(value)
            self.__dynamic_lookup[(name, value)] = field

    def parse_field(self, data, count, endian, timestamp, references, message, warn=False, **options):
        for name in self.references:
            if name in references:
                lookup = (name, references[name][0][0])  # drop units and take first value
                if lookup in self.__dynamic_lookup:
                    yield from message.profile_to_field(self.__dynamic_lookup[lookup]).parse_field(
                        data, count, endian, timestamp, references, message, warn=warn, **options)
                    return
        if warn:
            self._log.warning('Could not resolve dynamic field %s' % self.name)
        yield from super().parse_field(data, count, endian, timestamp, references, message, warn=warn, **options)


def MessageField(log, row, rows, types):
    log.debug('Parsing field %s' % row.field_name)
    if row.components:
        return CompositeField(log, row, types)
    else:
        peek = rows.peek()
        if row.field_no and peek and peek.field_name and peek.field_no is None:
            return DynamicField(log, row, rows, types)
        else:
            return RowField(log, row, types)


class Row(namedtuple('BaseRow',
                     'msg_name, field_no, field_name, field_type, array, components, scale, offset, ' +
                     'units, bits, accumulate, ref_name, ref_value, comment, products, example')):

    __slots__ = ()

    def __new__(cls, row):
        return super().__new__(cls, *tuple(row)[0:16])

    def single_int(self, log, value):
        try:
            return None if value is None else int(value)
        except ValueError:
            log.warning('Cannot parse "%s" as a single integer', value)
            return None
