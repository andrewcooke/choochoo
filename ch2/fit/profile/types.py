
import datetime as dt
from abc import abstractmethod
from collections import namedtuple
from re import compile
from struct import unpack

from .support import Named, Rows
from ...lib.data import WarnDict, WarnList

LITTLE, BIG = 0, 1


class AbstractType(Named):
    '''
    Root class for any kind of type in the system.
    '''

    def __init__(self, log, name, n_bytes, base_type=None):
        super().__init__(log, name)
        self.base_type = base_type
        self.n_bytes = n_bytes

    @abstractmethod
    def profile_to_internal(self, cell_contents):
        raise NotImplementedError('%s: %s' % (self.__class__.__name__, self.name))

    @abstractmethod
    def parse_type(self, bytes, count, endian, timestamp, **options):
        raise NotImplementedError('%s: %s' % (self.__class__.__name__, self.name))


class SimpleType(AbstractType):
    '''
    Value is extracted directly from the binary data.
    '''

    def __init__(self, log, name, n_bytes, func):
        super().__init__(log, name, n_bytes)
        self.__func = func

    def profile_to_internal(self, cell_contents):
        return self.__func(cell_contents)


class StructSupport(SimpleType):
    '''
    Most base types use stucts to unpack data.
    '''

    def __init__(self, log, name, n_bytes, func, bad):
        super().__init__(log, name, n_bytes, func)
        self.__bad = bad

    def _is_bad(self, data, endian, count, n_bits):
        total_bits = count * n_bits
        n_bytes = total_bits // 8
        bad = 255 if self.__bad else 0
        remaining = total_bits % 8
        if remaining:
            mask = (1 << remaining) - 1
            # endian matters here, because we need to know if the first or last byte is "incomplete"
            if endian:
                # big endian so most significant (and incomplete) byte at start
                rest_bad = all(datum == bad for datum in data[1:n_bytes+1])
                return rest_bad and (data[0] & mask) == (mask if self.__bad else 0)
            else:
                # small endian, so most significant (and incomplete) byte at end
                rest_bad = all(datum == bad for datum in data[:n_bytes])
                return rest_bad and (data[n_bytes] & mask) == (mask if self.__bad else 0)
        else:
            return all(datum == bad for datum in data[:n_bytes])

    def _unpack(self, data, formats, count, endian, n_bits, check_bad=True):
        # bad is 0 or 1 - all bits are this value
        if check_bad and self._is_bad(data, endian, count, n_bits):
            return None
        else:
            # n_bytes?  todo !!!!!!!!!!!
            return unpack(formats[endian] % count, data[0:count * self.n_bytes])


class String(SimpleType):

    # it may seem weird this returns a singleton tuple.  shouldn't it be treated like a
    # character field where count is the mutliplicity?  but dynamic fields treat it as
    # a single value...

    def __init__(self, log, name):
        super().__init__(log, name, 1, str)

    def parse_type(self, bytes, count, endian, timestamp, **options):
        return (str(b''.join(byte for byte in unpack('%dc' % count, bytes) if byte != b'\0'),
                    encoding='utf-8'),)


class Boolean(SimpleType):

    def __init__(self, log, name):
        super().__init__(log, name, 1, bool)

    def parse_type(self, bytes, count, endian, timestamp, **options):
        return tuple(bool(byte) for byte in bytes)


class AutoInteger(StructSupport):
    '''
    A whole pile of different integer types can all be parameterised by sign and size.
    '''

    pattern = compile(r'^([su]?)int(\d{1,2})(z?)$')

    size_to_format = {1: 'b', 2: 'h', 4: 'i', 8: 'q'}

    def __init__(self, log, name):
        match = self.pattern.match(name)
        self.signed = match.group(1) != 'u'
        n_bits = int(match.group(2))
        if n_bits % 8:
            raise Exception('Size of %r not a multiple of 8 bits' % name)
        bad = 0 if match.group(3) == 'z' else 1
        super().__init__(log, name, n_bits // 8, self.int, bad)
        if self.n_bytes not in self.size_to_format:
            raise Exception('Cannot unpack %d bytes as an integer' % self.n_bytes)
        format = self.size_to_format[self.n_bytes]
        if not self.signed:
            format = format.upper()
        self.formats = ['<%d' + format, '>%d' + format]

    @staticmethod
    def int(cell):
        if isinstance(cell, int):
            return cell
        else:
            return int(cell, 0)

    def parse_type(self, data, count, endian, timestamp, n_bits=None, **options):
        if n_bits is None: n_bits = self.n_bytes * 8
        return self._unpack(data, self.formats, count, endian, n_bits)


class AliasInteger(AutoInteger):
    '''
    An integer with an alternative name.
    '''

    def __init__(self, log, name, spec):
        super().__init__(log, spec)
        self.name = name


def timestamp_to_time(timestamp, tzinfo=dt.timezone.utc):
    return dt.datetime(1989, 12, 31, tzinfo=tzinfo) + dt.timedelta(seconds=timestamp)


def time_to_timestamp(time, tzinfo=dt.timezone.utc):
    return int((time - dt.datetime(1989, 12, 31, tzinfo=tzinfo)).total_seconds())


class Date(AliasInteger):

    def __init__(self, log, name, utc=True):
        super().__init__(log, name, 'uint32')
        self.__tzinfo = dt.timezone.utc if utc else None

    def convert(self, time, tzinfo=dt.timezone.utc):
        if time is not None and time >= 0x10000000:
            return timestamp_to_time(time, tzinfo=tzinfo)
        else:
            raise Exception('Strange timestamp: %d' % time)

    def parse_type(self, data, count, endian, timestamp, raw_time=False, **options):
        times = super().parse_type(data, count, endian, timestamp, raw_time=raw_time, **options)
        if not raw_time:
            times = tuple(self.convert(time, tzinfo=self.__tzinfo) for time in times)
        return times


class Date16(AliasInteger):

    def __init__(self, log, name, utc=True):
        super().__init__(log, name, 'uint16')
        self.__tzinfo = dt.timezone.utc if utc else None

    @staticmethod
    def convert(time, timestamp, tzinfo=dt.timezone.utc):
        # https://www.thisisant.com/forum/viewthread/6374
        current = time_to_timestamp(timestamp, tzinfo=tzinfo)
        current += (time - (current & 0xffff)) & 0xffff
        return timestamp_to_time(current, tzinfo=tzinfo)

    def parse_type(self, data, count, endian, timestamp, raw_time=False, **options):
        times = super().parse_type(data, count, endian, timestamp, raw_time=raw_time, **options)
        if not raw_time:
            times = tuple(self.convert(time, timestamp, tzinfo=self.__tzinfo) for time in times)
        return times


class AutoFloat(StructSupport):

    pattern = compile(r'^float(\d{1,2})$')

    size_to_format = {2: 'e', 4: 'f', 8: 'd'}

    def __init__(self, log, name):
        match = self.pattern.match(name)
        n_bits = int(match.group(1))
        if n_bits % 8:
            raise Exception('Size of %r not a multiple of 8 bits' % name)
        super().__init__(log, name, n_bits // 8, float, 1)
        if self.n_bytes not in self.size_to_format:
            raise Exception('Cannot unpack %d bytes as a float' % self.n_bytes)
        format = self.size_to_format[self.n_bytes]
        self.formats = ['<%d' + format, '>%d' + format]

    def parse_type(self, data, count, endian, timestamp, n_bits=None, **options):
        if n_bits is None: n_bits = self.n_bytes * 8
        return self._unpack(data, self.formats, count, endian, n_bits)


class Mapping(AbstractType):

    def __init__(self, log, row, rows, types, warn=False):
        name = row.type_name
        base_type_name = row.base_type
        base_type = types.profile_to_type(base_type_name, auto_create=True)
        super().__init__(log, name, base_type.n_bytes, base_type=base_type)
        self._profile_to_internal = WarnDict(log, 'No internal value for profile %r') if warn else dict()
        self._internal_to_profile = WarnDict(log, 'No profile value for internal %r') if warn else dict()
        while rows:
            peek = rows.peek()
            if peek.type_name or peek.value_name is None or peek.value is None:
                return
            self.__add_mapping(next(rows))

    def profile_to_internal(self, cell_contents):
        return self._profile_to_internal[cell_contents]

    def internal_to_profile(self, value):
        return self._internal_to_profile[value]

    def safe_internal_to_profile(self, value):
        try:
            return self.internal_to_profile(value)
        except KeyError:
            return value

    def parse_type(self, bytes, size, endian, timestamp, map_values=True, **options):
        values = self.base_type.parse_type(bytes, size, endian, timestamp, check_bad=False, **options)
        if map_values and values:
            values = tuple(self.safe_internal_to_profile(value) for value in values)
        return values

    def __add_mapping(self, row):
        profile = row.value_name
        internal = self.base_type.profile_to_internal(row.value)
        self._profile_to_internal[profile] = internal
        self._internal_to_profile[internal] = profile


BASE_TYPE_NAMES = ['enum', 'sint8', 'uint8', 'sint16', 'uint16', 'sint32', 'uint32',
                   'string', 'float32', 'float64',
                   'uint8z', 'uint16z', 'uint32z', 'byte', 'sint64', 'uint64', 'uint64z']


class Types:

    def __init__(self, log, sheet, warn=False):
        self.__log = log
        self.__profile_to_type = WarnDict(log, 'No type for profile %r')
        # these are not 'base types' in the same sense as types having base types.
        # rather, they are the 'base (integer) types' described in the docs
        self.base_types = WarnList(log, 'No base type for number %r')
        self.overrides = set()
        self.__add_known_types()
        rows = Rows(sheet, wrapper=Row)
        for row in rows:
            if row[0] and row.type_name[0].isupper():
                self.__log.debug('Skipping %s' % (row,))
            elif row[0]:
                # self.__log.info('Parsing type %s' % row[0])
                self.__add_type(Mapping(self.__log, row, rows, self, warn=warn))

    def __add_known_types(self):
        # these cannot be inferred from name
        self.__add_type(String(self.__log, 'string'))
        self.__add_type(AliasInteger(self.__log, 'enum', 'uint8'))
        self.__add_type(AliasInteger(self.__log, 'byte', 'uint8'))
        # these can be inferred
        for name in BASE_TYPE_NAMES:
            self.profile_to_type(name, auto_create=True)
            self.base_types.append(self.profile_to_type(name))
        # this is in the spreadsheet, but not in the doc
        self.__add_type(Boolean(self.__log, 'bool'))
        # these are defined in the spreadsheet, but the interpretation is in comments
        self.__add_override(Date(self.__log, 'date_time', utc=True))
        self.__add_override(Date(self.__log, 'local_date_time', utc=False))
        self.__add_override(Date16(self.__log, 'timestamp_16', utc=True))

    def __add_override(self, type):
        self.overrides.add(type.name)
        self.__add_type(type)

    def __add_type(self, type):
        if type.name in self.__profile_to_type:
            duplicate = self.__profile_to_type[type.name]
            if duplicate.n_bytes == type.n_bytes:
                self.__log.warning('Ignoring duplicate type for %r' % type.name)
            else:
                raise Exception('Duplicate type for %r with differing size (%d  %d)' %
                                (type.name, type.n_bytes, duplicate.n_bytes))
        else:
            self.__profile_to_type[type.name] = type

    def is_type(self, name):
        return name in self.__profile_to_type

    def profile_to_type(self, name, auto_create=False):
        try:
            return self.__profile_to_type[name]
        except KeyError:
            if auto_create:
                for cls in (AutoFloat, AutoInteger):
                    match = cls.pattern.match(name)
                    if match:
                        self.__log.info('Auto-adding type %s for %r' % (cls.__name__, name))
                        self.__add_type(cls(self.__log, name))
                        return self.profile_to_type(name)
            raise


class Row(namedtuple('BaseRow',
                     'type_name, base_type, value_name, value, comment')):

    __slots__ = ()

    def __new__(cls, row):
        return super().__new__(cls, *tuple(row)[0:5])

