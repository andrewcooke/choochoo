
import datetime as dt
from abc import abstractmethod
from collections import defaultdict, Counter
from struct import unpack, pack

from ..profile.fields import TypedField, TIMESTAMP_GLOBAL_TYPE, DynamicField
from ..profile.types import timestamp_to_time, time_to_timestamp
from ...lib.data import WarnDict, tohex


class Identity:

    def __init__(self, name, counter):
        self.name = name
        counter[name] += 1
        self.count = counter[name]
        self.__counter = counter

    def __repr__(self):
        current = self.__counter[self.name]
        if current == 1:
            return self.name
        else:
            return '%s (defn %d/%d)' % (self.name, self.count, current)


class Token:

    __slots__ = ('tag', 'is_user', 'data')

    def __init__(self, tag, is_user, data):
        self.tag = tag
        self.is_user = is_user
        self.data = data

    def __str__(self):
        return '%s %s' % (self.tag, tohex(self.data))

    def __len__(self):
        return len(self.data)


class ValidateToken(Token):

    @abstractmethod
    def validate(self, data, log, quiet=False):
        raise NotImplementedError()

    def _error(self, msg, log, quiet):
        if quiet:
            log.warn(msg)
        else:
            raise Exception(msg)


FIT = b'.FIT'


class FileHeader(ValidateToken):

    def __init__(self, data):
        super().__init__('HDR', False, data[:data[0]])
        self.protocol_version = data[1]
        self.profile_version = unpack('<H', data[2:4])[0]
        self.data_size = unpack('<I', data[4:8])[0]
        self.data_type = b''.join(unpack('4c', data[8:12]))
        if len(self) > 13:
            self.checksum = unpack('<H', data[12:14])[0]
            self.has_checksum = self.checksum != 0
        else:
            self.has_checksum = False

    def validate(self, data, log, quiet=False):
        if len(data) != self.data_size + len(self) + 2:
            self._error('Data length (%d/%d+%d+2=%d)' % (len(data), self.data_size, len(self),
                                                         self.data_size + len(self) + 2), log, quiet)
        if self.data_type != FIT:
            self._error('Data type incorrect (%s)' % (self.data_type,), log, quiet)
        if self.has_checksum:
            checksum = Checksum.crc(data[0:12])
            if checksum != self.checksum:
                self._error('Inconsistent checksum (%04x/%04x)' % (checksum, self.checksum), log, quiet)

    def repair(self, data, log):
        data_size = len(data) - len(self) - 2
        if data_size != self.data_size:
            log.warn('Fixing header data size: %d -> %d' % (self.data_size, data_size))
            self.data_size = data_size
            self.data[4:8] = pack('<I', self.data_size)
        if self.data_type != FIT:
            log.warn('Fixing header data type: %s -> %s' % (self.data_type, FIT))
            self.data_type = FIT
            self.data[8:12] = pack('4c', self.data_type)
        if self.has_checksum:
            checksum = Checksum.crc(self.data[0:12])
            if checksum != self.checksum:
                log.warn('Fixing header checksum: %04x -> %04x' % (self.checksum, checksum))
                self.checksum = checksum
                self.data[12:14] = pack('<H', checksum)

    def describe_fields(self, types):
        yield '%s - header' % tohex(self.data[0:1])
        yield '%s - protocol version' % tohex(self.data[1:2])
        yield '%s - profile version' % tohex(self.data[2:4])
        yield '%s - data size' % tohex(self.data[4:8])
        yield '%s - data type' % tohex(self.data[8:12])
        if self.has_checksum:
            yield '%s - checksum' % tohex(self.data[12:14])


class Defined(Token):

    __slots__ = ('definition', 'timestamp')

    def __init__(self, tag, data, state, local_message_type):
        self.definition = state.definitions[local_message_type]
        if self.definition.timestamp_field:
            self.__parse_timestamp(data, state)
        self.timestamp = state.timestamp
        super().__init__(tag, True, data[0:self.definition.size])
        if self.definition.global_message_no == 206:
            self.__parse_field_definition(state)
            self.is_user = False

    def __parse_timestamp(self, data, state):
        field = self.definition.timestamp_field
        state.timestamp = field.field.type.parse(data[field.start:field.finish], 1,
                                                 self.definition.endian, state.timestamp)[0]

    def __parse_field_definition(self, state):
        record = self.parse().force()
        developer_index = record.attr.developer_data_index[0][0]
        number = record.attr.field_definition_number[0][0]
        # todo - we don't really need to convert name to type just to extract name below
        base_type = state.types.base_types[
            state.types.profile_to_type('fit_base_type').profile_to_internal(
                record.attr.fit_base_type_id[0][0])]
        # todo - more fields (optional)
        name = record.attr.field_name[0][0]
        units = record.attr.units[0][0]
        state.dev_fields[developer_index][number] = \
            TypedField(state.log, name, number, units, None, None, None, base_type.name, state.types)

    def parse(self, **options):
        return self.definition.message.parse(self.data, self.definition, self.timestamp, **options)

    def describe_fields(self, types):
        yield '%s - header (msg %d - %s)' % \
              (tohex(self.data[0:1]), self.data[0] & 0x0f, self.definition.message.name)
        for field in sorted(self.definition.fields, key=lambda field: field.start):
            if field.name == 'timestamp':
                yield '%s - %s (%s) %s' % (tohex(self.data[field.start:field.finish]), field.name,
                                           field.base_type.name, self.timestamp)
            else:
                yield '%s - %s (%s)' % (tohex(self.data[field.start:field.finish]), field.name, field.base_type.name)

    def describe_csv(self):
        record = self.parse(map_values=False, raw_time=True, rtn_composite=True)
        yield self.__class__.__name__
        yield self.definition.local_message_type
        yield record.name
        for name, (values, units) in record.data:
            yield name
            yield '' if values is None else '|'.join(str(value) for value in values)
            yield '' if units is None else units


class Data(Defined):

    __slots__ = ()

    def __init__(self, data, state):
        super().__init__('DTA', data, state, data[0] & 0x0f)


class CompressedTimestamp(Defined):

    __slots__ = ()

    def __init__(self, data, state):
        offset = data[0] & 0x1f
        if not isinstance(state.timestamp, dt.datetime):
            raise Exception('int timestamp')
        timestamp = time_to_timestamp(state.timestamp)
        rollover = offset < timestamp & 0x1f
        state.timestamp = timestamp_to_time((timestamp & 0xffffffe0) + offset + (0x20 if rollover else 0))
        super().__init__('TIM', data, state, data[0] & 0x60 >> 5)


class Field:

    def __init__(self, size, field, base_type):

        self.size = size
        self.field = field
        self.name = self.field.name if self.field else 'unknown'
        self.base_type = base_type

        self.count = self.size // base_type.size
        # set by definition later
        self.start = 0
        self.finish = 0


class Definition(Token):

    def __init__(self, data, state, overhead=6, tag='DFN'):
        self.local_message_type = data[0] & 0x0f
        self.is_user = False
        self.references = set()
        self.timestamp_field = None
        self.endian = data[2] & 0x01
        self.global_message_no = unpack('<>'[self.endian]+'H', data[3:5])[0]
        self.message = state.messages.number_to_message(self.global_message_no)
        self.identity = Identity(self.message.name, state.definition_counter)
        self.fields = self._process_fields(self._make_fields(data, state))
        super().__init__(tag, False, data[0:overhead+3*len(self.fields)])
        state.definitions[self.local_message_type] = self

    def _make_fields(self, data, state):
        yield from self.__fields(data, state.types)

    def __fields(self, data, types):
        for i in range(data[5]):
            yield self.__field(data[6 + i * 3:6 + (i + 1) * 3], self.message, types)

    def __field(self, data, message, types):
        number, size, base = data
        try:
            field = message.number_to_field(number)
        except KeyError:
            field = None
        base_type = types.base_types[base & 0xf]
        return Field(size, field, base_type)

    def _process_fields(self, fields):
        offset = 1  # header
        fields = tuple(fields)
        for field in fields:
            field.start = offset
            offset += field.size
            field.finish = offset
            if field.field and \
                    (field.field.number == TIMESTAMP_GLOBAL_TYPE or field.field.name == 'timestamp_16'):
                self.timestamp_field = field
            if field.field and isinstance(field.field, DynamicField):
                self.references.update(field.field.references)
        self.size = offset
        return tuple(sorted(fields, key=lambda field: 1 if field.field and isinstance(field.field, DynamicField) else 0))

    def accumulate(self, field, values):
        # todo - need test for this (currently clearly broken)
        n = len(values)
        if field in self.__sums:
            sum = self.__sums[field]
            while len(sum) < n:
                self.__sums += (0,)
            while len(values) < len(sum):
                values += (0,)
            sum = tuple(s + v for s, v in zip(sum, values))
            self.__sums[field] = sum
        else:
            self.__sums[field] = values
        return self.__sums[field][0:n]

    def describe_fields(self, types):
        yield '%s - header (msg %d)' % (tohex(self.data[0:1]), self.local_message_type)
        yield '%s - reserved' % tohex(self.data[1:2])
        yield '%s - architecture' % tohex(self.data[2:3])
        yield '%s - msg no (%s)' % (tohex(self.data[3:5]), self.message.name)
        yield '%s - no of fields' % tohex(self.data[5:6])
        for i in range(self.data[5]):
            data = self.data[6 + i*3:9 + i*3]
            field = self.__field(data, self.message, types)
            mult = '' if field.count == 1 else 'x%d' % field.count
            yield '  %s - fld %d: %s (%s%s)' % (tohex(data), i, field.name, field.base_type.name, mult)

    def describe_csv(self):
        yield 'Definition'
        yield self.local_message_type
        yield self.message.name
        for field in self.fields:
            yield field.name
            yield field.count
            yield ''


class DeveloperDefinition(Definition):

    def __init__(self, data, state):
        super().__init__(data, state, overhead=7, tag='DFX')

    def _make_fields(self, data, state):
        yield from super()._make_fields(data, state)
        for field_data in self.__field_data(data):
            yield self.__field(field_data, state.dev_fields)

    def __field_data(self, data):
        offset = data[5] * 3 + 7
        n_dev_fields = data[offset-1]
        for i in range(n_dev_fields):
            yield data[offset + i * 3:offset + (i + 1) * 3]

    def __field(self, data, dev_fields):
        number, size, developer_index = data
        field = dev_fields[developer_index][number]
        return Field(size, field, field.type)

    def describe_fields(self, types):
        yield from super().describe_fields(types)
        offset = self.data[5] * 3 + 7
        yield '%s - no of dev fields' % tohex(self.data[offset-1:offset])
        for field_data in self.__field_data(self.data):
            fdn, size, ddi = field_data
            yield '  %s - dev fld %d/%d' % (tohex(field_data), fdn, ddi)


class Checksum(ValidateToken):

    @staticmethod
    def crc(data):

        CRC = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
               0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]

        checksum = 0
        for byte in data:
            tmp = CRC[checksum & 0xf]
            checksum = (checksum >> 4) & 0xfff
            checksum = checksum ^ tmp ^ CRC[byte & 0xf]
            tmp = CRC[checksum & 0xf]
            checksum = (checksum >> 4) & 0xfff
            checksum = checksum ^ tmp ^ CRC[(byte >> 4) & 0xf]
        return checksum

    def __init__(self, data):
        super().__init__('CRC', False, data[-2:])
        self.all_data = data[:-2]
        self.checksum = unpack('<H', self.data)[0]

    def validate(self, offset, log, quiet=False):
        # length already validated in header
        if len(self.all_data) != offset:
            self._error('Did not consume all data (%d/%d)' % (len(self.all_data), offset), log, quiet)
        checksum = self.crc(self.all_data)
        if checksum != self.checksum:
            self._error('Bad checksum (%04x/%04x)' % (checksum, self.checksum), log, quiet)

    def repair(self, data, log):
        checksum = self.crc(data[:-2])
        if checksum != self.checksum:
            log.warn('Fixing final checksum: %04x -> %04x' % (self.checksum, checksum))
            self.checksum = checksum
            self.data = pack('<H', checksum)

    def describe_fields(self, types):
        yield '%s - checksum' % tohex(self.data)


def token_factory(data, state):
    header = data[0]
    if header & 0x80:
        return CompressedTimestamp(data, state)
    else:
        if header & 0x40:
            if header & 0x20:
                return DeveloperDefinition(data, state)
            else:
                return Definition(data, state)
        else:
            return Data(data, state)


class State:

    def __init__(self, log, types, messages):
        self.log = log
        self.types = types
        self.messages = messages
        self.dev_fields = defaultdict(dict)
        self.definitions = WarnDict(log, 'No definition for local message type %s')
        self.definition_counter = Counter()
        self.timestamp = None

    def copy(self):
        copy = State(self.log, self.types, self.messages)
        copy.dev_fields.update(self.dev_fields)
        copy.definitions.update(self.definitions)
        copy.definition_counter.update(self.definition_counter)
        copy.timestamp = self.timestamp
        return copy

