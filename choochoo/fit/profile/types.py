
import datetime as dt
from abc import abstractmethod
from collections import namedtuple
from re import compile
from struct import unpack

from .support import Named, Rows
from ...lib.data import WarnDict, WarnList

LITTLE, BIG = 0, 1


class AbstractType(Named):

    def __init__(self, log, name, size, base_type=None):
        super().__init__(log, name)
        self.base_type = base_type
        self.size = size

    @abstractmethod
    def profile_to_internal(self, cell_contents):
        raise NotImplementedError('%s: %s' % (self.__class__.__name__, self.name))

    @abstractmethod
    def parse(self, bytes, count, endian, **options):
        raise NotImplementedError('%s: %s' % (self.__class__.__name__, self.name))


class BaseType(AbstractType):

    def __init__(self, log, name, size, func):
        super().__init__(log, name, size)
        self.__func = func

    def profile_to_internal(self, cell_contents):
        return self.__func(cell_contents)


class StructSupport(BaseType):

    def _pack_bad(self, value):
        bad = (bytearray(self.size), bytearray(self.size))
        for endian in (LITTLE, BIG):
            bytes = value
            for i in range(self.size):
                j = i if endian == LITTLE else self.size - i - 1
                bad[endian][j] = bytes & 0xff
                bytes >>= 8
        return bad

    def _is_bad(self, data, bad):
        size = len(bad)
        count = len(data) // size
        return all(bad == data[size*i:size*(i+1)] for i in range(count))

    def _unpack(self, data, formats, bad, count, endian):
        if self._is_bad(data, bad[endian]):
            return None
        else:
            return unpack(formats[endian] % count, data[0:count * self.size])


class String(BaseType):

    # it may seem weird this returns a singleton tuple.  shouldn't it be treated like a
    # character field where count is the mutliplicity?  but dynamic fields treat it as
    # a single value...

    def __init__(self, log, name):
        super().__init__(log, name, 1, str)

    def parse(self, bytes, count, endian, **options):
        return (str(b''.join(byte for byte in unpack('%dc' % count, bytes) if byte != b'\0'),
                    encoding='utf-8'),)


class Boolean(BaseType):

    def __init__(self, log, name):
        super().__init__(log, name, 1, bool)

    def parse(self, bytes, count, endian, **options):
        return tuple(bool(byte) for byte in bytes)


class AutoInteger(StructSupport):

    pattern = compile(r'^([su]?)int(\d{1,2})(z?)$')

    size_to_format = {1: 'b', 2: 'h', 4: 'i', 8: 'q'}

    def __init__(self, log, name):
        match = self.pattern.match(name)
        self.signed = match.group(1) != 'u'
        bits = int(match.group(2))
        if bits % 8:
            raise Exception('Size of %r not a multiple of 8 bits' % name)
        super().__init__(log, name, bits // 8, self.int)
        if self.size not in self.size_to_format:
            raise Exception('Cannot unpack %d bytes as an integer' % self.size)
        format = self.size_to_format[self.size]
        if not self.signed:
            format = format.upper()
        self.formats = ['<%d' + format, '>%d' + format]
        self.bad = self._pack_bad(0 if match.group(3) == 'z' else 2 ** (bits - (1 if self.signed else 0)) - 1)

    @staticmethod
    def int(cell):
        if isinstance(cell, int):
            return cell
        else:
            return int(cell, 0)

    def parse(self, data, count, endian, **options):
        result = self._unpack(data, self.formats, self.bad, count, endian)
        if result is not None and self.size == 1:
            result = bytes(result)
        return result


class AliasInteger(AutoInteger):

    def __init__(self, log, name, spec):
        super().__init__(log, spec)
        self.name = name


class Date(AliasInteger):

    def __init__(self, log, name, utc, to_datetime=True):
        super().__init__(log, name, 'uint32')
        self.__tzinfo = dt.timezone.utc if utc else None
        self.__to_datetime = to_datetime

    @staticmethod
    def convert(time, tzinfo=dt.timezone.utc):
        if time is not None and time >= 0x10000000 :
            return dt.datetime(1989, 12, 31, tzinfo=tzinfo) + dt.timedelta(seconds=time)
        else:
            return time

    def parse(self, data, count, endian, cvt_times=None, **options):
        times = super().parse(data, count, endian, cvt_times=None, **options)
        if (cvt_times is None and self.__to_datetime) or cvt_times:
            times = tuple(self.convert(time, tzinfo=self.__tzinfo) for time in times)
        return times


class AutoFloat(StructSupport):

    pattern = compile(r'^float(\d{1,2})$')

    size_to_format = {2: 'e', 4: 'f', 8: 'd'}

    def __init__(self, log, name):
        match = self.pattern.match(name)
        bits = int(match.group(1))
        if bits % 8:
            raise Exception('Size of %r not a multiple of 8 bits' % name)
        super().__init__(log, name, bits // 8, float)
        if self.size not in self.size_to_format:
            raise Exception('Cannot unpack %d bytes as a float' % self.size)
        format = self.size_to_format[self.size]
        self.formats = ['<%d' + format, '>%d' + format]
        self.bad = self._pack_bad(2 ** bits - 1)

    def parse(self, data, count, endian, **options):
        return self._unpack(data, self.formats, self.bad, count, endian)


class Mapping(AbstractType):

    def __init__(self, log, row, rows, types, warn=False):
        name = row.type_name
        base_type_name = row.base_type
        base_type = types.profile_to_type(base_type_name, auto_create=True)
        super().__init__(log, name, base_type.size, base_type=base_type)
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

    def parse(self, bytes, size, endian, map_values=True, **options):
        values = self.base_type.parse(bytes, size, endian, map_values=map_values, **options)
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
        self.__add_type(Date(self.__log, 'date_time', True))
        self.__add_type(Date(self.__log, 'local_date_time', False))

    def __add_type(self, type):
        if type.name in self.__profile_to_type:
            duplicate = self.__profile_to_type[type.name]
            if duplicate.size == type.size:
                self.__log.warn('Ignoring duplicate type for %r' % type.name)
            else:
                raise Exception('Duplicate type for %r with differing size (%d  %d)' %
                                (type.name, type.size, duplicate.size))
        else:
            self.__profile_to_type.add_named(type)

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
                        self.__log.warn('Auto-adding type %s for %r' % (cls.__name__, name))
                        self.__add_type(cls(self.__log, name))
                        return self.profile_to_type(name)
            raise


class Row(namedtuple('BaseRow',
                     'type_name, base_type, value_name, value, comment')):

    __slots__ = ()

    def __new__(cls, row):
        return super().__new__(cls, *tuple(row)[0:5])

