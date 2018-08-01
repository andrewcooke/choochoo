
from binascii import hexlify
from collections import namedtuple, Counter
from struct import unpack

from choochoo.fit.profile import LITTLE, load_profile, HEADER_FIELDS, HEADER_GLOBAL_TYPE, read_profile, \
    TIMESTAMP_GLOBAL_TYPE, Date


def parse_all(log, fit_path, profile_path=None):
    data, types, messages, header = load(log, fit_path, profile_path=profile_path)
    return (msg.parse() for msg in Tokenizer(log, data, types, messages))


def load(log, fit_path, profile_path=None):
    if profile_path:
        _nlog, types, messages = read_profile(log, profile_path)
    else:
        types, messages = load_profile(log)
    log.debug('Read profile')
    with open(fit_path, 'rb') as input:
        data =input.read()
    log.debug('Read "%s"' % fit_path)
    header = read_header(log, data, types, messages)
    log.debug('Header: %s' % (header,))
    stripped, checksum = strip_header_crc(data)
    log.debug('Checked length')
    check_crc(stripped, checksum)
    log.debug('Checked checksum')
    return stripped, types, messages, header


def strip_header_crc(data):
    offset, length = unpack('<BxxxI', data[:8])
    size = offset + length + 2
    if len(data) != size:
        raise Exception('Bad length (%d / %d)' % (len(data), size))
    checksum = unpack('<H', data[-2:])[0]
    return data[offset:-2], checksum


def header_defn(log, types, messages):
    message = messages.number_to_message(HEADER_GLOBAL_TYPE)
    return Definition(log, Identity(message.name, 0), LITTLE, message,
                      [Field(log, n, field[1] * types.profile_to_type(field[2]).size,
                             message.number_to_field(n),
                             types.profile_to_type(field[2]))
                       for n, field in enumerate(HEADER_FIELDS)],
                      {'header_size'})  # this needed as reference for optional field logic


def read_header(log, data, types, messages):
    header = messages.profile_to_message('HEADER')
    defn = header_defn(log, types, messages)
    return header.parse(data[0:defn.size], defn).as_dict()


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


class Msg(namedtuple('MsgTuple', 'definition data timestamp')):

    __slots__ = ()

    def parse(self):
        return self.definition.message.parse(self.data, self.definition, self.timestamp)


class DataMsg(Msg): pass


class TimedMsg(Msg): pass


class Tokenizer:

    def __init__(self, log, data, types, messages, offset=0):
        self.__log = log
        self.__data = data
        self.__offset = offset
        self.__types = types
        self.__messages = messages
        self.__timestamp = None
        self.__definiton_counter = Counter()
        self.__definitions = {}
        self.__parse_date = Date(log, 'timestamp', True, to_datetime=False)

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
        global_type = unpack('<>'[endian]+'H', self.__data[self.__offset+3:self.__offset+5])[0]
        n_fields = self.__data[self.__offset+5]
        self.__log.debug('Definition: %s' % hexlify(self.__data[self.__offset:self.__offset+6+n_fields*3]))
        message = self.__messages.number_to_message(global_type)
        self.__log.info('Definition for message "%s"' % message.name)
        self.__definiton_counter[global_type] += 1
        self.__definitions[local_type] = \
            Definition(self.__log, Identity(message.name, self.__definiton_counter[global_type]), endian, message,
                       [self.__make_field(self.__data[self.__offset+6+i*3:self.__offset+6+(i+1)*3], message)
                        for i in range(n_fields)])
        self.__offset += 6 + n_fields * 3
        if extended: raise NotImplementedError()

    def __make_field(self, bytes, message):
        number, size, base = bytes
        field = None
        if message:
            try:
                field = message.number_to_field(number)
            except KeyError:
                field = None
                self.__log.warn('No field %d for message %s' % (number, message.name))
        base_type = self.__types.base_types[base & 0xf]
        return Field(self.__log, number, size, field, base_type)

    def __data_msg(self, local_type):
        defn = self.__definitions[local_type]
        data = self.__data[self.__offset+1:self.__offset+1+defn.size]
        if defn.has_timestamp:
            self.__timestamp = self.__parse_timestamp(defn, data)
            self.__log.debug('New timestamp: %s' % self.__timestamp)
        self.__offset += 1 + defn.size
        # include timestamp here so that things like laps can be correlated with timed data
        return DataMsg(defn, data, self.__timestamp)

    def __parse_timestamp(self, defn, data):
        field = defn.fields[defn.number_to_index[TIMESTAMP_GLOBAL_TYPE]]
        return self.__parse_date.parse(data[field.start:field.finish], 1, defn.endian)

    def __compressed_timestamp_msg(self, local_type, time_offset):
        rollover = time_offset < self.__timestamp & 0x1f
        self.__timestamp = (self.__timestamp & 0xffffffe0) + time_offset + (0x20 if rollover else 0)
        defn = self.__definitions[local_type]
        payload = self.__data[self.__offset+1:self.__offset+1+defn.size]
        self.__offset += 1 + defn.size
        return TimedMsg(defn, payload, self.__timestamp)


class Field:

    def __init__(self, log, number, size, field, base_type):
        self.__log = log
        self.number = number
        self.size = size
        self.field = field
        self.base_type = base_type
        self.count = self.size // base_type.size
        # set by definiton
        self.start = 0
        self.finish = 0


class Identity:

    def __init__(self, name, count):
        self.name = name
        self.count = count
        # todo - total count

    def __str__(self):
        if self.count:
            return '%s (defn %d)' % (self.name, self.count)
        else:
            return self.name


class Definition:

    def __init__(self, log, identity, endian, message, fields, references=None):
        self.__log = log
        self.identity = identity
        self.endian = endian
        self.message = message
        # set offsets before ordering
        self.__set_field_offsets(fields)
        self.fields = list(sorted(fields, key=lambda field: 1 if field.field and field.field.is_dynamic else 0))
        self.size = sum(field.size for field in self.fields)
        self.number_to_index = {}
        self.has_timestamp = False
        self.references = references if references else set()
        self.__scan_fields(fields)

    def __scan_fields(self, fields):
        for index, field in enumerate(fields):
            number = field.number
            self.number_to_index[field.number] = index
            if number == TIMESTAMP_GLOBAL_TYPE:
                self.has_timestamp = True
            if field.field and field.field.is_dynamic:
                self.references.update(field.field.references)

    @staticmethod
    def __set_field_offsets(fields):
        offset = 0
        for field in fields:
            field.start = offset
            offset += field.size
            field.finish = offset
