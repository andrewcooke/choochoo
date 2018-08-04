
from collections import namedtuple, Counter, defaultdict
from struct import unpack

from .profile import LITTLE, load_profile, HEADER_FIELDS, HEADER_GLOBAL_TYPE, read_profile, \
    TIMESTAMP_GLOBAL_TYPE, Date, SimpleMessageField
from .records import chain, join_values, append_units


def parse_all(log, fit_path, profile_path=None):
    data, types, messages, header = load(log, fit_path, profile_path=profile_path)
    return Tokenizer(log, data, types, messages)


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
    return Definition(log, Identity(message.name, Counter()), LITTLE, message,
                      [Field(log, field[1] * types.profile_to_type(field[2]).size,
                             message.number_to_field(n),
                             types.profile_to_type(field[2]))
                       for n, field in enumerate(HEADER_FIELDS)],
                      (),
                      {'header_size'})  # this needed as reference for optional field logic


def read_header(log, data, types, messages):
    header = messages.profile_to_message('HEADER')
    defn = header_defn(log, types, messages)
    return header.parse(data[0:defn.size], defn).as_dict(filter=chain(join_values, append_units)).data


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


class Header:

    __slots__ = ('__byte')

    def __init__(self, byte):
        self.__byte = byte

    def is_timestamp(self):
        return self.__byte & 0x80

    def is_definition(self):
        return self.__byte & 0x40

    def local_type(self):
        if self.is_timestamp():
            return (self.__byte & 0x60) >> 5
        else:
            return self.__byte & 0x0f

    def time_offset(self):
        return self.__byte & 0x1f

    def is_extended(self):
        return self.__byte & 0x20


class Tokenizer:

    def __init__(self, log, data, types, messages, offset=0):

        self.__log = log
        self.__data = data
        self.__types = types
        self.__messages = messages
        self.__offset = offset

        self.__timestamp = None
        self.__defn_counter = Counter()
        self.__definitions = {}
        self.__parse_date = Date(log, 'timestamp', True, to_datetime=False)
        self.__dev_fields = defaultdict(dict)

    def __iter__(self):
        while self.__offset < len(self.__data):
            header = Header(self.__data[self.__offset])
            if header.is_definition():
                self.__offset += self.__add_definition(header.local_type(), header.is_extended())
            else:
                defn = self.__definitions[header.local_type()]
                data = self.__data[self.__offset+1:self.__offset+1+defn.size]
                self.__offset += 1 + defn.size
                if header.is_timestamp():
                    yield self.__parse_and_save_dev_fields(defn, self.__timed_msg(defn, data, header.time_offset()))
                else:
                    yield self.__parse_and_save_dev_fields(defn, self.__data_msg(defn, data))

    def __parse_and_save_dev_fields(self, defn, msg):
        record = msg.parse()
        # we don't care about developer data because the application id has no meaning to us
        # so we simply accept new developer indices when they appear in developer fields
        if defn.message.number == 206:
            record = record.force()
            self.__field_description(defn, record)
        return record

    def __field_description(self, defn, record):
        developer_index = record.attr.developer_data_index[0][0]
        number = record.attr.field_definition_number[0][0]
        # ooof...
        base_type = self.__types.base_types[
            defn.fields[2].field.type.profile_to_internal(record.attr.fit_base_type_id[0][0])]
        name = record.attr.field_name[0][0]
        units = record.attr.units[0][0]
        self.__dev_fields[developer_index][number] = SimpleMessageField(self.__log, name, None, units, base_type)

    def __data_msg(self, defn, data):
        if defn.timestamp_field:
            field = defn.timestamp_field
            self.__timestamp = self.__parse_date.parse(data[field.start:field.finish], 1, defn.endian)[0]
        # include timestamp here so that things like laps can be correlated with timed data
        return DataMsg(defn, data, self.__timestamp)

    def __timed_msg(self, defn, data, time_offset):
        rollover = time_offset < self.__timestamp & 0x1f
        self.__timestamp = (self.__timestamp & 0xffffffe0) + time_offset + (0x20 if rollover else 0)
        return TimedMsg(defn, data, self.__timestamp)

    def __add_definition(self, local_type, extended):
        endian = self.__data[self.__offset+2] & 0x1
        global_type = unpack('<>'[endian]+'H', self.__data[self.__offset+3:self.__offset+5])[0]
        message = self.__messages.number_to_message(global_type)
        identity = Identity(message.name, self.__defn_counter)
        n_fields = self.__data[self.__offset+5]
        fields = tuple(self.__fields(self.__field,self.__offset+6, n_fields, message))
        offset = 6 + n_fields * 3
        if extended:
            n_dev_fields = self.__data[self.__offset+offset]
            dev_fields = tuple(self.__fields(self.__dev_field, self.__offset+offset+1, n_dev_fields))
            offset += 1 + n_dev_fields * 3
        else:
            dev_fields = ()
        self.__definitions[local_type] = Definition(self.__log, identity, endian, message, fields, dev_fields)
        return offset

    def __fields(self, field, offset, n_fields, *args):
        for i in range(n_fields):
            yield field(self.__data[offset + i * 3:offset + (i + 1) * 3], *args)

    def __field(self, data, message):
        number, size, base = data
        try:
            field = message.number_to_field(number)
        except KeyError:
            field = None
            self.__log.warn('No field %d for message %s' % (number, message.name))
        base_type = self.__types.base_types[base & 0xf]
        return Field(self.__log, size, field, base_type)

    def __dev_field(self, data):
        number, size, developer_index = data
        field = self.__dev_fields[developer_index][number]
        return Field(self.__log, size, field, field.type)


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


class Definition:

    def __init__(self, log, identity, endian, message, fields, dev_fields, references=None):

        self.__log = log
        self.identity = identity
        self.endian = endian
        self.message = message
        self.references = references if references else set()

        self.timestamp_field = None
        self.size = 0
        self.fields = self.__process_fields(fields, dev_fields)

    def __process_fields(self, fields, dev_fields):
        all_fields = tuple(fields) + tuple(dev_fields)
        offset = 0
        for field in all_fields:
            field.start = offset
            offset += field.size
            field.finish = offset
            if field.field and field.field.number == TIMESTAMP_GLOBAL_TYPE:
                self.timestamp_field = field
            if field.field and field.field.is_dynamic:
                self.references.update(field.field.references)
        self.size = offset
        return tuple(sorted(all_fields, key=lambda field: 1 if field.field and field.field.is_dynamic else 0))
