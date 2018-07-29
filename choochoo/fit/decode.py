
from binascii import hexlify
from collections import namedtuple
from struct import unpack

from choochoo.fit.profile import LITTLE, load_profile, HEADER_FIELDS, HEADER_GLOBAL_TYPE, read_profile


def decode_all(log, fit_path, profile_path):
    if profile_path:
        _nlog, types, messages = read_profile(log, profile_path)
    else:
        types, messages = load_profile(log)
    log.debug('Read profile')
    data = read_path(fit_path)
    log.debug('Read "%s"' % fit_path)
    _offset, header = read_header(log, data, types, messages)
    log.debug('Header: %s' % header)
    stripped, checksum = strip_header_crc(data)
    log.debug('Checked length')
    check_crc(stripped, checksum)
    log.debug('Checked checksum')
    tokenizer = Tokenizer(log, stripped, types, messages)
    for value in apply(tokenizer, [(DataMsg, drop)]):
        print(value)


def read_path(path):
    with open(path, 'rb') as input:
        return input.read()


def strip_header_crc(data):
    offset, length = unpack('<BxxxI', data[:8])
    size = offset + length + 2
    if len(data) != size:
        raise Exception('Bad length (%d / %d)' % (len(data), size))
    checksum = unpack('<H', data[-2:])[0]
    return data[offset:-2], checksum


def header_defn(log, types, messages):
    message = messages.number_to_message(HEADER_GLOBAL_TYPE)
    return Definition(log, LITTLE, message,
                      [Field(log, n, field[1],
                             message.number_to_field(n),
                             types.profile_to_type(field[2]))
                       for n, field in enumerate(HEADER_FIELDS)])


def read_header(log, data, types, messages):
    header = messages.profile_to_message('HEADER')
    return header.raw_to_internal(data, header_defn(log, types, messages))


CRC = [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
       0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]


def check_crc(data, reference):
    checksum = 0
    for byte in data:
        tmp = CRC[checksum & 0xf]
        checksum = (checksum >> 4) & 0xfff
        checksum = checksum ^ tmp ^ CRC[byte & 0xf]
        tmp = CRC[checksum & 0xf]
        checksum = (checksum >> 4) & 0xfff
        checksum = checksum ^ tmp ^ CRC[(byte >> 4) & 0xf]
    if checksum != reference:
        raise Exception('Bad checksum (%04x / %04x)' % (checksum, reference))


ENDIAN = '<>'


DataMsg = namedtuple('DataMsg', 'definition data')

TimedMsg = namedtuple('TimedMsg', 'definition data time')


class Tokenizer:

    def __init__(self, log, data, types, messages, offset=0):
        self.__log = log
        self.__data = data
        self.__offset = offset
        self.__types = types
        self.__messages = messages
        self.__timestamp = None
        self.__definitions = {}

    def __iter__(self):
        while self.__offset < len(self.__data):
            header = self.__data[self.__offset]
            self.__log.debug('Header %02x' % header)
            if header & 0x80:
                local_type = (header & 0x60) >> 5
                time_offset = header & 0x1f
                yield self.__compressed_timestamp_msg(local_type, time_offset)
            else:
                local_type = header & 0x0f
                if header & 0x40:
                    extended = header & 0x20
                    self.__definition_msg(local_type, extended)
                else:
                    yield self.__data_msg(local_type)

    def __definition_msg(self, local_type, extended):
        endian = self.__data[self.__offset+2] & 0x1
        global_type = unpack(ENDIAN[endian]+'H', self.__data[self.__offset+3:self.__offset+5])[0]
        n_fields = self.__data[self.__offset+5]
        self.__log.debug('Definition: %s' % hexlify(self.__data[self.__offset:self.__offset+6+n_fields*3]))
        try:
            message = self.__messages.number_to_message(global_type)
            self.__log.info('Definition for message "%s"' % self.message.name)
        except KeyError:
            message = None
            self.__log.warn('No message %d' % global_type)
        self.__definitions[local_type] = \
            Definition(self.__log, endian, message,
                       [self.__make_field(self.__data[self.__offset+6+i*3:self.__offset+6+(i+1)*3], message)
                        for i in range(n_fields)])
        self.__offset += 6 + n_fields * 3
        # todo - check for timestamp?
        if extended: raise NotImplementedError()

    def __make_field(self, bytes, message):
        number, size, base = bytes
        field = None
        if self.message:
            try:
                field = self.message.number_to_field(number)
            except KeyError:
                field = None
                self.__log.warn('No field %d for message %d (%s)' % (number, self.message))
        base_type = self.__types.base_types[base & 0xf]
        return Field(self.__log, number, size, field, base_type)

    def __data_msg(self, local_type):
        definition = self.__definitions[local_type]
        payload = self.__data[self.__offset+1:self.__offset+1+definition.size]
        self.__offset += 1 + definition.size
        # todo - check for timestamp?
        return DataMsg(definition, payload)

    def __compressed_timestamp_msg(self, local_type, time_offset):
        rollover = time_offset < self.__timestamp & 0x1f
        self.__timestamp = (self.__timestamp & 0xffffffe0) + time_offset + (0x20 if rollover else 0)
        definition = self.__definitions[local_type]
        payload = self.__data[self.__offset+1:self.__offset+1+definition.size]
        self.__offset += 1 + definition.size
        # todo - check for timestamp?
        return TimedMsg(definition, payload, self.__timestamp)


class Field:

    def __init__(self, log, number, size, field, base_type):
        self.__log = log
        self.number = number
        self.size = size
        self.field = field
        self.base_type = base_type


class Definition:

    def __init__(self, log, endian, message, fields):
        self.__log = log
        self.endian = endian
        self.message = message
        self.fields = fields
        self.size = sum(field.size for field in self.fields)


def apply(source, pipeline):
    for value in source:
        for (cls, transform) in pipeline:
            if isinstance(value, cls):
                value = transform(value)
            if value is None:
                break
        if value is not None:
            yield value


def drop(value): pass



