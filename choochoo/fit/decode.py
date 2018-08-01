
from binascii import hexlify
from collections import namedtuple
from pprint import PrettyPrinter
from struct import unpack

from choochoo.fit.profile import LITTLE, load_profile, HEADER_FIELDS, HEADER_GLOBAL_TYPE, read_profile, \
    TIMESTAMP_GLOBAL_TYPE, Date, WithUnits


def decode_all(log, fit_path, profile_path=None):
    data, types, messages, header = load(log, fit_path, profile_path=profile_path)
    tokenizer = Tokenizer(log, data, types, messages)
    time_series = {}
    for value in pipeline(tokenizer,
                          [(instances(DataMsg), expand_as_dict(log)),
                           # (DataMsg, collect_as_tuples(log, time_series)),
                           (instances(dict), to_degrees),
                           (instances(dict), delete_undefined_values),
                           (instances(dict), display_and_drop(log))
                           ]):
        print(value)
    PrettyPrinter().pprint(time_series)
    for name in time_series:
        print(name)
        print([len(x) for x in time_series[name]])


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
    log.debug('Header: %s' % header)
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
    return Definition(log, LITTLE, message,
                      [Field(log, n, field[1] * types.profile_to_type(field[2]).size,
                             message.number_to_field(n),
                             types.profile_to_type(field[2]))
                       for n, field in enumerate(HEADER_FIELDS)],
                      {'header_size'})  # this needed as reference for optional field logic


def read_header(log, data, types, messages):
    header = messages.profile_to_message('HEADER')
    defn = header_defn(log, types, messages)
    result = header.parse_as_dict(data[0:defn.size], defn)
    result['MESSAGE'] = 'HEADER'
    return result


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


DataMsg = namedtuple('DataMsg', 'definition data timestamp')

TimedMsg = namedtuple('TimedMsg', 'definition data timestamp')


class Tokenizer:

    def __init__(self, log, data, types, messages, offset=0):
        self.__log = log
        self.__data = data
        self.__offset = offset
        self.__types = types
        self.__messages = messages
        self.__timestamp = None
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
        global_type = unpack(ENDIAN[endian]+'H', self.__data[self.__offset+3:self.__offset+5])[0]
        n_fields = self.__data[self.__offset+5]
        self.__log.debug('Definition: %s' % hexlify(self.__data[self.__offset:self.__offset+6+n_fields*3]))
        message = self.__messages.number_to_message(global_type)
        self.__log.info('Definition for message "%s"' % message.name)
        self.__definitions[local_type] = \
            Definition(self.__log, endian, message,
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


class Definition:

    def __init__(self, log, endian, message, fields, references=None):
        self.__log = log
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


def pipeline(source, pipeline):
    for value in source:
        for actions in pipeline:
            for action in actions:
                if action.test(value):
                    value = action(value)
                if value is None:
                    break
            if value is None:
                break
        if value is not None:
            yield value


def exhaust(pipeline):
    for _ in pipeline:
        pass


def add_test(test):
    def decorator(f):
        f.test = test
        return f
    return decorator


pipeline_any = add_test(lambda value: True)


def pipeline_instance(*cls_list):
    def test(value):
        if cls_list:
            return any(isinstance(value, cls) for cls in cls_list)
        else:
            return True
    return add_test(test)


def drop(log, *cls):
    @pipeline_instance(*cls)
    def action(msg):
        return None
    return [action]


def display_and_drop(log, *cls):
    @pipeline_instance(*cls)
    def action(msg):
        log.debug('Drop: %s' % (msg,))
    return [action]


def save_definitions(log, defintions):
    @pipeline_instance(DataMsg, TimedMsg)
    def action(msg):
        defintions[msg.definition.message.name] = msg.definition
        return msg
    return [action]


def expand_as_dict(log, *cls, add_timestamp=True):
    @pipeline_instance(*cls)
    def action(msg):
        defn = msg.definition
        result = defn.message.parse_as_dict(msg.data, msg.definition)
        result['MESSAGE'] = msg.definition.message.name
        if add_timestamp:
            result['TIMESTAMP'] = (msg.timestamp, 's')
        return result
    return [action]


def expand_as_tuple(log, *cls, add_timestamp=True):
    @pipeline_instance(*cls)
    def action(msg):
        defn = msg.definition
        result = defn.message.parse_as_tuple(msg.data, msg.definition)
        if add_timestamp:
            return (msg.definition.message.name, msg.timestamp) + result
        else:
            return (msg.definition.message.name,) + result
    return [action]


def collect_tuples(log, definitions, results, add_timestamp=True):
    @pipeline_instance(tuple)
    def action(msg):
        name = msg[0]
        if name not in results:
            defn = definitions[name]
            header = tuple(field.field.name if field.field else field.number for field in defn.fields)
            if add_timestamp:
                header = ('TIMESTAMP',) + header
            results[name] = header
        results[name].append(msg)
    return [action]


def collect(log, results, *cls):
    @pipeline_instance(*cls)
    def action(msg):
        results.append(msg)
    return action


def to_degrees(log, new_units='°'):
    @pipeline_instance(dict)
    def data_action(msg):
        for name, pair in list(msg.items()):
            if name[0].islower():
                value, old_units = pair
                if old_units == 'semicircles':
                    msg[name] = (value * 180 / 2**31, new_units)
        return msg
    @pipeline_instance(WithUnits)
    def timed_action(msg):
        def filter(pair):
            try:
                value, units = pair
                if units == 'semicircles':
                    pair = (value * 180 / 2**31, new_units)
            except TypeError:
                pass
            return pair
        msg = WithUnits((name, filter(pair)) for name, pair in msg)
        return msg
    return [data_action, timed_action]


def delete_undefined_values(log):
    def dict(msg):
        for name, pair in list(msg.items()):
            if pair is None:
                del msg[name]
            else:
                try:
                    if pair[0] is None:
                        del msg[name]
                except TypeError:
                    pass
        return msg
    return filter


def clean_unknown_messages(log):
    def filter(msg):
        if not msg['MESSAGE'][0].isupper():
            return msg
    return filter


def clean_unknown_fields(log):
    def filter(msg):
        for name, value in list(msg.items()):
            if name[0].isdigit():
                del msg[name]
        return msg
    return filter


def clean_empty_messages(log):
    def filter(msg):
        if msg:
            return msg
    return filter


def clean_fields(log, fields):
    def filter(msg):
        for name, value in list(msg.items()):
            if name in fields:
                del msg[name]
        return msg
    return filter
