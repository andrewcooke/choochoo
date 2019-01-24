
import datetime as dt
from abc import abstractmethod
from collections import namedtuple
from re import compile
from struct import unpack, pack

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

    def is_bad(self, bytes, count, endian):
        return False

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

    def _pack_bad(self, value):
        bad = (bytearray(self.n_bytes), bytearray(self.n_bytes))
        for endian in (LITTLE, BIG):
            bytes = value
            for i in range(self.n_bytes):
                j = i if endian == LITTLE else self.n_bytes - i - 1
                bad[endian][j] = bytes & 0xff
                bytes >>= 8
        return bad

    def _all_bad(self, data, bad, count):
        return all(bad == data[self.n_bytes*i:self.n_bytes*(i+1)] for i in range(count))

    # currently this ignores scale and offset!!!
    def _pack(self, values, formats, count, endian):
        return pack(formats[endian] % count, *values)

    # scale and offset have to be at this level because of how bad values when count > 1 are handled
    def _unpack(self, data, formats, bad, count, endian, scale=1, offset=0, check_bad=True,
                name=None, accumulators=None, n_bits=None, **options):
        if check_bad and self._all_bad(data, bad[endian], count):
            return None
        elif accumulators and name in accumulators:
            if count > 1:
                raise Exception('Cannot accumulate multiple fields (%s: %d)' % (name, count))
            return self.__unpack_acc(bytearray(data[:self.n_bytes]), formats[endian] % 1, scale, offset,
                                     name, accumulators, n_bits, endian)
        else:
            if (scale == 1 and offset == 0) or self.name == 'enum':   # enums are not scaled
                # fast and preserves integers
                return unpack(formats[endian] % count, data[:self.n_bytes * count])
            elif count == 1:  # if no check, scale single bad values
                return (unpack(formats[endian] % 1, data[:self.n_bytes])[0] / scale - offset,)
            else:  # match weird CSV behaviour
                return tuple(self.__unpack_scaled(data[self.n_bytes*i:self.n_bytes*(i+1)], formats[endian],
                                                  bad[endian], scale, offset) for i in range(count))

    def __unpack_scaled(self, data, format, bad, scale, offset):
        value = unpack(format % 1, data)[0]
        if data == bad or (scale == 1 and offset == 0):
            # the java CSV program returns isolated bad values in multiples as unscaled
            return value
        else:
            return value / scale - offset

    def __unpack_acc(self, data, format, scale, offset, name, accumulators, n_bits, endian):
        short = unpack(format, data)[0]
        if accumulators[name] is not None:
            prev_data, prev_long = accumulators[name]
            if n_bits:
                mask = (1 << n_bits) - 1
                prev_short = prev_long & mask
            elif short < prev_long:
                raise Exception('Full accumulated field has decreased in value (%s: %d/%d)' %
                                (name, short, prev_long))  # or n_bits was missing...
            if short >= prev_long:  # initial phase of simple growth OR a full read
                long = short
            else:  # otherwise, need all bits
                data = self.__merge_bytes(prev_data, data, n_bits, endian)
                if short < prev_short:  # rollover?
                    data = self.__add_bit(data, n_bits, endian)
                long = unpack(format, data)[0]
        else:
            long = short
        accumulators[name] = (data, long)
        if scale == 1 and offset == 0:
            return (long,)
        else:
            return (long / scale - offset,)

    def __merge_bytes(self, prev_data, data, n_bits, endian, index=None):
        now = min(8, n_bits)
        later = max(0, n_bits - now)
        if endian == LITTLE:
            if index is None: index = 0
            prev_data[index] = self.__merge_bits(prev_data[index], data[index], now)
            if later:
                self.__merge_bytes(prev_data, data, later, endian, index=index+1)
        else:
            if index is None: index = -1
            prev_data[index] = self.__merge_bits(prev_data[index], data[index], now)
            if later:
                self.__merge_bytes(prev_data, data, later, endian, index=index-1)
        return prev_data

    def __merge_bits(self, prev_data, data, n_bits):
        mask = (1 << n_bits) - 1
        return (prev_data & ~mask) | (data & mask)

    def __add_bit(self, data, n_bits, endian):
        value = 1 << (n_bits % 8)
        index = n_bits // 8
        if endian == LITTLE:
            while value and index < len(data):
                value += data[index]
                data[index] = value & 0xff
                value = (value & 0x100) >> 8
                index += 1
        else:
            while value and index >= 0:
                value += data[index]
                data[index] = value & 0xff
                value = (value & 0x100) >> 8
                index -= 1
        return data


class String(SimpleType):

    def __init__(self, log, name):
        super().__init__(log, name, 1, str)

    def parse_type(self, bytes, count, endian, timestamp, **options):
        try:
            value = str(b''.join(unpack('%dc' % count, bytes)), encoding='utf-8')
            while value and value[-1] == '\u0000': value = value[:-1]
            return value.split('\u0000')  # inferred from CSV handling of weird data in tests
        except UnicodeDecodeError:
            # this gets us close to what garmin generates in CSV files
            bytes = bytearray(b % 0x7f for b in bytes)
            while bytes and bytes[-1] == 0: bytes = bytes[:-1]
            return tuple(b.decode('ascii') for b in bytes.split(b'\0'))


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
        super().__init__(log, name, n_bits // 8, self.int)
        if self.n_bytes not in self.size_to_format:
            raise Exception('Cannot unpack %d bytes as an integer' % self.n_bytes)
        format = self.size_to_format[self.n_bytes]
        if not self.signed:
            format = format.upper()
        self.__formats = ['<%d' + format, '>%d' + format]
        self.__bad = self._pack_bad(0 if match.group(3) == 'z' else 2 ** (n_bits - (1 if self.signed else 0)) - 1)

    @staticmethod
    def int(cell):
        if isinstance(cell, int):
            return cell
        else:
            return int(cell, 0)

    def is_bad(self, bytes, count, endian):
        return self._all_bad(bytes, self.__bad[endian], count)

    def parse_type(self, data, count, endian, timestamp, check_bad=True, **options):
        return self._unpack(data, self.__formats, self.__bad, count, endian, check_bad=check_bad, **options)

    def pack_type(self, values, count, endian):
        return self._pack(values, self.__formats, count, endian)


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


class BadTimestamp(Exception): pass


class Date(AliasInteger):

    def __init__(self, log, name, utc=True):
        super().__init__(log, name, 'uint32')
        self.__tzinfo = dt.timezone.utc if utc else None

    def convert(self, time, tzinfo=dt.timezone.utc):
        if time is not None:
            return timestamp_to_time(time, tzinfo=tzinfo)

    def parse_type(self, data, count, endian, timestamp, raw_time=False, **options):
        times = super().parse_type(data, count, endian, timestamp, raw_time=raw_time, **options)
        if times and not raw_time:
            times = tuple(self.convert(time, tzinfo=self.__tzinfo) for time in times)
        return times

    def pack_type(self, values, count, endian):
        return super().pack_type([time_to_timestamp(value) for value in values], count, endian)


class Date16(AliasInteger):

    def __init__(self, log, name, utc=True):
        super().__init__(log, name, 'uint16')
        self.__tzinfo = dt.timezone.utc if utc else None

    def convert(self, time, timestamp, tzinfo=dt.timezone.utc):
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
        super().__init__(log, name, n_bits // 8, float)
        if self.n_bytes not in self.size_to_format:
            raise Exception('Cannot unpack %d bytes as a float' % self.n_bytes)
        format = self.size_to_format[self.n_bytes]
        self.__formats = ['<%d' + format, '>%d' + format]
        self.__bad = self._pack_bad(2 ** n_bits - 1)

    def is_bad(self, bytes, count, endian):
        return self._all_bad(bytes, self.__bad[endian], count)

    def parse_type(self, data, count, endian, timestamp, check_bad=True, **options):
        return self._unpack(data, self.__formats, self.__bad, count, endian, check_bad=check_bad, **options)


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

    # default here for check_bad sets whether mappings can be considered bad or not
    # tests against CSV suggest they can (battery_level)
    def parse_type(self, bytes, size, endian, timestamp, map_values=True, check_bad=True, **options):
        values = self.base_type.parse_type(bytes, size, endian, timestamp, check_bad=check_bad, **options)
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

