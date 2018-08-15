
from collections import defaultdict, Counter
from struct import unpack

from .profile.fields import TypedField, TIMESTAMP_GLOBAL_TYPE, DynamicField
from .profile.profile import read_profile, load_profile
from .profile.types import Date
from ..lib.data import WarnDict


class Identity:

    def __init__(self, name, counter):
        self.name = name
        counter[name] += 1
        self.count = counter[name]
        self.__counter = counter

    def __repr__(self):
        # this assumes all instances have been evaluated, which is risky given
        # the lazy approach, but the cost of an error is low
        current = self.__counter[self.name]
        if current == 1:
            return self.name
        else:
            return '%s (defn %d/%d)' % (self.name, self.count, current)


class FileHeaderToken:

    def __init__(self, data):
        self.is_user = False
        self.__len = data[0]
        self.protocol_version = data[1]
        self.profile_version = unpack('<H', data[2:4])[0]
        self.data_size = unpack('<I', data[4:8])[0]
        self.data_type = b''.join(unpack('4c', data[8:12]))
        if self.__len > 13:
            self.checksum = unpack('<H', data[12:14])[0]
            self.has_checksum = self.checksum != 0
        else:
            self.has_checksum = False

    def validate(self, data):
        if self.__len < 12:
            raise Exception('Header too short (%d)' % self.__len)
        if len(data) != self.data_size + self.__len + 2:
            raise Exception('Data length (%d/%d)' % (len(data), self.data_size + self.__len + 2))
        if self.data_type != b'.FIT':
            raise Exception('Data type incorrect (%s)' % (self.data_type,))
        if self.has_checksum:
            checksum = ChecksumToken.crc(data[0:12])
            if checksum != self.checksum:
                raise Exception('Inconsistent checksum (%04x/%04x)' % (checksum, self.checksum))

    def __len__(self):
        return self.__len


class DefinedToken:

    def __init__(self, data, state, local_message_type):
        self.definition = state.definitions[local_message_type]
        self.data = data[0:len(self.definition)]
        if self.definition.timestamp_field:
            field = self.definition.timestamp_field
            state.timestamp = state.date.parse(data[field.start:field.finish], 1, self.definition.endian)[0]
        self.timestamp = state.timestamp
        if self.definition.global_message_no == 206:
            self.is_user = False
            record = self.parse()
            record.force()
            developer_index = record.attr.developer_data_index[0][0]
            number = record.attr.field_definition_number[0][0]
            base_type = state.types.base_types[
                state.types.profile_to_type('fit_base_type').profile_to_internal(
                    record.attr.fit_base_type_id[0][0])]
            name = record.attr.field_name[0][0]
            units = record.attr.units[0][0]
            state.dev_fields[developer_index][number] = \
                TypedField(self.__log, name, number, units, None, None, None, base_type, state.types)
        else:
            self.is_user = True

    def parse(self):
        return self.definition.message.parse(self.data, self.definition, self.timestamp)

    def __len__(self):
        return self.definition.size


class DataToken(DefinedToken):

    def __init__(self, data, state):
        super().__init__(data, state, data[0] & 0x0f)


class CompressedTimsestampToken(DefinedToken):

    def __init__(self, data, state):
        offset = data[0] & 0x1f
        rollover = offset < state.timestamp & 0x1f
        state.timestamp = (state.timestamp & 0xffffffe0) + offset + (0x20 if rollover else 0)
        super().__init__(data, state, data[0] & 0x60 >> 5)


class Field:

    def __init__(self, log, size, field, base_type):

        self.__log = log
        self.size = size
        self.field = field
        self.base_type = base_type

        self.count = self.size // base_type.size
        # set by definition later
        self.start = 0
        self.finish = 0


class DefinitionToken:

    def __init__(self, data, state):
        self.is_user = False
        self.references = set()
        self.timestamp_field = None
        local_message_type = data[0] & 0x0f
        state.definitions[local_message_type] = self
        self.endian = data[2] & 0x01
        self.global_message_no = unpack('<>'[self.endian]+'H', data[3:5])[0]
        self.message = state.messages.number_to_message(self.global_message_no)
        self.identity = Identity(self.message.name, state.definition_counter)
        self.fields = self._process_fields(self._make_fields(data, self.message, state))
        self._overhead = 6

    def _make_fields(self, data, message, state):
        n_fields = data[5]
        for i in range(n_fields):
            yield self.__field(data[6 + i * 3:6 + (i + 1) * 3], message, state)

    def __field(self, data, message, state):
        number, size, base = data
        try:
            field = message.number_to_field(number)
        except KeyError:
            field = None
        base_type = state.types.base_types[base & 0xf]
        return Field(state.log, size, field, base_type)

    def _process_fields(self, fields):
        offset = 1
        fields = tuple(fields)
        for field in fields:
            field.start = offset
            offset += field.size
            field.finish = offset
            if field.field and field.field.number == TIMESTAMP_GLOBAL_TYPE:
                self.timestamp_field = field
            if field.field and isinstance(field.field, DynamicField):
                self.references.update(field.field.references)
        self.size = offset
        return tuple(sorted(fields, key=lambda field: 1 if field.field and isinstance(field.field, DynamicField) else 0))

    def __len__(self):
        return len(self.fields) * 3 + self._overhead

    def accumulate(self, field, values):
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


class DeveloperDefinitionToken(DefinitionToken):

    def __init__(self, data, state):
        super().__init__(data, state)
        self._overhead = 7

    def _make_fields(self, data, message, state):
        fields = tuple(super()._make_fields(data, message, state))
        yield from fields
        offset = len(fields) * 3 + 7
        n_dev_fields = data[offset-1]
        for i in n_dev_fields:
            yield self.__field(data[offset + i * 3:offset + (i + 1) * 3], state)

    def __field(self, data, state):
        number, size, developer_index = data
        field = state.dev_fields[developer_index][number]
        return Field(state.log, size, field, field.type)


class ChecksumToken:

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
        self.is_user = False
        self.data = data[:-2]
        self.checksum = unpack('<H', data[-2:])[0]

    def validate(self, offset, file_header):
        # length already validated in header
        if len(self.data) != offset:
            raise Exception('Did not consume all data (%d/%d)' % (len(self.data), offset))
        checksum = self.crc(self.data)
        if checksum != self.checksum:
            raise Exception('Bad checksum (%04x / %04x)' % (checksum, self.checksum))


def Token(data, state):
    header = data[0]
    if header & 0x80:
        return CompressedTimsestampToken(data, state)
    else:
        if header & 0x40:
            if header & 0x20:
                return DeveloperDefinitionToken(data, state)
            else:
                return DefinitionToken(data, state)
        else:
            return DataToken(data, state)


class State:

    def __init__(self, log, types, messages):
        self.log = log
        self.types = types
        self.messages = messages
        self.dev_fields = defaultdict(dict)
        self.definitions = WarnDict(log, 'No definition for local message type %s')
        self.definition_counter = Counter()
        self.date = Date(log, 'timestamp', True, to_datetime=False)
        self.timestamp = None


def tokens(data, state):
    file_header = FileHeaderToken(data)
    offset = len(file_header)
    yield file_header
    file_header.validate(data)
    while len(data) - offset > 2:
        token = Token(data[offset:], state)
        offset += len(token)
        yield token
    checksum = ChecksumToken(data)
    yield checksum
    checksum.validate(offset, file_header)


def parse_all(log, fit_path, profile_path=None):
    data, types, messages = load(log, fit_path, profile_path=profile_path)
    state = State(log, types, messages)
    for token in tokens(data, state):
        if token.is_user:
            yield token.parse()


def load(log, fit_path, profile_path=None):
    # todo separate?
    if profile_path:
        _nlog, types, messages = read_profile(log, profile_path)
    else:
        types, messages = load_profile(log)
    log.debug('Read profile')
    with open(fit_path, 'rb') as input:
        data =input.read()
    return data, types, messages
