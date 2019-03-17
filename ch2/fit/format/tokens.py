
from abc import abstractmethod
from collections import defaultdict, Counter
from logging import getLogger
from re import sub
from struct import unpack, pack

from .records import LazyRecord, merge_duplicates
from ..profile.fields import TypedField, TIMESTAMP_GLOBAL_TYPE, DynamicField, CompositeField
from ..profile.types import timestamp_to_time, time_to_timestamp
from ...lib.data import WarnDict, tohex
from ...stoats.names import S

log = getLogger(__name__)
FIELD_DESCRIPTION = 206


class Identity:
    '''
    A unique ID that identifies a particular message type (a combination of message name
    and the particular definition used).
    '''

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
    '''
    A chunk of the file.  Subclasses into different token types below.

    tag - a simple string describing the type of token (HDR etc)
    is_user - does this contain user data? (alternatively, it;s internal data for parsing)
    data - the bytes from the input file.
    '''

    __slots__ = ('tag', 'is_user', 'data')

    def __init__(self, tag, is_user, data):
        self.tag = tag
        self.is_user = is_user
        self.data = data

    def __str__(self):
        return '%s %s' % (self.tag, tohex(self.data))

    def __len__(self):
        return len(self.data)

    def _fake_field(self, key, value):
        if isinstance(value, tuple) or isinstance(value, list):
            values, units = value
            if not isinstance(values, tuple) and not isinstance(values, list):
                values = (values,)
        else:
            values, units = (value,), None
        return key, (values, units)

    def _fake_record(self, name, **kargs):
        return LazyRecord(name, None, Identity(name, Counter()), None,
                          [self._fake_field(key, value) for key, value in kargs.items()])

    @abstractmethod
    def parse_token(self, **options):
        raise NotImplementedError()

    def _describe_csv_header(self, record):
        yield self.__class__.__name__

    def _describe_csv_data(self, record, field_names=None):
        for name, (values, units) in record.data.items():
            if not field_names or name in field_names:
                yield name
                yield '' if values is None else '|'.join(str(value) for value in values)
                yield '' if units is None else units

    def describe_csv(self, record_names=None, field_names=None, internal=False, **options):
        record = self.parse_token(map_values=False, raw_time=True, rtn_composite=True,
                                  **options).force(merge_duplicates)
        if not record_names or record.name in record_names:
            yield from self._describe_csv_header(record)
            yield from self._describe_csv_data(record, field_names=field_names)

    def describe_fields(self, types):
        for name, (values, units) in self.parse_token(raw_data=True).data:
            value = tohex(values[0])
            yield '%s - %s' % (value, sub('_', ' ', name))

    def repair_timestamp(self, timestamp):
        pass


class ValidateToken(Token):
    '''
    A Token that can be validated.  Provides support for quiet or noisy validation.
    '''

    @abstractmethod
    def validate(self, data, log, quiet=False):
        raise NotImplementedError()

    def _error(self, msg, log, quiet):
        if quiet:
            log.warning(msg)
        else:
            raise Exception(msg)


FIT = b'.FIT'


class FileHeader(ValidateToken):
    '''
    The (single) header Token that starts a file.

    Contains extra functionality to allow modification when fixing FIT files.
    '''

    def __init__(self, data):
        super().__init__('HDR', False, data[:data[0]])
        self.header_size = data[0]
        self.protocol_version = data[1]
        self.profile_version = unpack('<H', data[2:4])[0]
        self.data_size = unpack('<I', data[4:8])[0]
        self.data_type = b''.join(unpack('4c', data[8:12]))
        if len(self) > 13:
            self.checksum = unpack('<H', data[12:14])[0]
            self.has_checksum = self.checksum != 0
        else:
            self.has_checksum = False

    def validate(self, data, log, quiet=False, header_size=None, protocol_version=None, profile_version=None):
        if self.header_size < 12:
            self._error('Header size too small (%d)' % self.header_size, log, quiet)
        if self.header_size not in (12, 14):
            log.warning('Header size not standard (%d/12-14)' % self.header_size)
        if header_size is not None:
            if self.header_size != header_size:
                self._error('Header size incorrect (%d/%d)' % (self.header_size, header_size), log, quiet)
        if protocol_version is not None:
            if self.profile_version != protocol_version:
                self._error('Protocol version incorrect (%d%d)' % (self.protocol_version, protocol_version), log, quiet)
        if profile_version is not None:
            if self.profile_version != profile_version:
                self._error('Profile version incorrect (%d%d)' % (self.profile_version, profile_version), log, quiet)
        if len(data) != self.data_size + len(self) + 2:
            self._error('Data size incorrect (%d/%d+%d+2=%d)' % (len(data), self.data_size, len(self),
                                                                 self.data_size + len(self) + 2), log, quiet)
        if self.data_type != FIT:
            self._error('Data type incorrect (%s)' % (self.data_type,), log, quiet)
        if self.has_checksum:
            checksum = Checksum.crc(data[0:12])
            if checksum != self.checksum and self.checksum:
                self._error('Inconsistent checksum (%04x/%04x)' % (checksum, self.checksum), log, quiet)

    def repair(self, data, log, header_size=None, protocol_version=None, profile_version=None):
        if header_size is not None and self.header_size != header_size:
            log.warning('Changing header size: %d -> %d' % (self.header_size, header_size))
            self.header_size = header_size
            self.data = [0] * self.header_size
            self.data[0] = self.header_size
        # next two are applied even if unchanged because resizing removes
        if protocol_version is not None:
            if protocol_version != self.protocol_version:
                log.warning('Changing protocol version: %d -> %d' % (self.protocol_version, protocol_version))
            self.protocol_version = protocol_version
            self.data[1] = self.protocol_version
        if profile_version is not None:
            if profile_version != self.profile_version:
                log.warning('Changing profile version: %d -> %d' % (self.profile_version, profile_version))
            self.profile_version = profile_version
            self.data[2:4] = pack('<H', self.profile_version)
        data_size = len(data) - len(self) - 2
        if data_size != self.data_size:
            log.warning('Fixing header data size: %d -> %d' % (self.data_size, data_size))
            self.data_size = data_size
            self.data[4:8] = pack('<I', self.data_size)
        if self.data_type != FIT:
            log.warning('Fixing header data type: %s -> %s' % (self.data_type, FIT))
            self.data_type = FIT
            self.data[8:12] = self.data_type
        if self.header_size >= 14:
            checksum = Checksum.crc(self.data[0:12])
            if not self.has_checksum or checksum != self.checksum:
                log.warning('Fixing header checksum: %04x -> %04x' %
                            (self.checksum if self.has_checksum else 0, checksum))
                self.checksum = checksum
                self.data[12:14] = pack('<H', checksum)
                self.has_checksum = True

    def parse_token(self, raw_data=False, **options):
        data = {'header_size': self.data[0:1] if raw_data else self.header_size,
                'protocol_version': self.data[1:2] if raw_data else self.protocol_version,
                'profile_version': self.data[2:4] if raw_data else self.profile_version,
                'data_size': (self.data[4:8] if raw_data else self.data_size, 'bytes'),
                'data_type': self.data[8:12] if raw_data else self.data_type}
        if self.has_checksum:
            data['checksum'] = self.data[12:14] if raw_data else self.checksum
        return self._fake_record('file_header', **data)


class Defined(Token):
    '''
    A chunk of data from a FIT file that is associated with a single local message.  Bundled with
    the Definition for that type, which itself contains a reference to the Message and Fields the data contain.
    '''

    __slots__ = ('definition', 'timestamp', '_accumulators')

    def __init__(self, tag, data, state, local_message_type):
        self.definition = state.definitions[local_message_type]
        if self.definition.timestamp_field:
            self.__parse_timestamp(data, state)
        self.timestamp = state.timestamp
        self._accumulators = state.accumulators
        if len(data) < self.definition.size:
            raise Exception('Insufficient data for %s (%d/%d)' %
                            (self.definition.identity, len(data), self.definition.size))
        super().__init__(tag, True, data[0:self.definition.size])

    def __parse_timestamp(self, data, state):
        field = self.definition.timestamp_field
        times = field.field.type.parse_type(data[field.start:field.finish], 1, self.definition.endian, state.timestamp,
                                            check_bad=False)
        if times:
            state.timestamp = times[0]
        else:
            raise Exception('Could not parse timestamp')

    def parse_token(self, **options):
        return self.definition.message.parse_message(self.data, self.definition, self.timestamp,
                                                     accumulators=self._accumulators, **options)

    def describe_fields(self, types):
        yield '%s - header (local message type %d - %s)' % \
              (tohex(self.data[0:1]), self.data[0] & 0x0f, self.definition.identity)
        for field in sorted(self.definition.fields, key=lambda field: field.start):
            if field.name == 'timestamp':
                yield '%s - %s (%s) %s' % (tohex(self.data[field.start:field.finish]), field.name,
                                           field.base_type.name, self.timestamp)
            else:
                yield '%s - %s (%s)' % (tohex(self.data[field.start:field.finish]), field.name, field.base_type.name)

    def _describe_csv_header(self, record):
        yield self.__class__.__name__
        yield self.definition.local_message_type
        yield record.name

    def repair_timestamp(self, state):
        if self.definition.timestamp_field:
            field = self.definition.timestamp_field
            self.data[field.start:field.finish] = field.field.type.pack_type((state.timestamp,),
                                                                             field.count, self.definition.endian)


class DeveloperField(Defined):

    def __init__(self, data, state):
        super().__init__('FLD', data, state, data[0] & 0x0f)
        self.__parse_field_definition(state)
        self.is_user = False

    def __parse_field_definition(self, state):
        record = self.parse_token().force()
        developer_index = record.attr.developer_data_index[0][0]
        number = record.attr.field_definition_number[0][0]
        base_type = state.types.profile_to_type(record.attr.fit_base_type_id[0][0])
        # todo - more fields (optional)
        name = record.attr.field_name[0][0]
        units = record.attr.units[0][0]
        state.dev_fields[developer_index][number] = \
            TypedField(log, name, number, units, None, None, None, base_type.name, state.types)

    # todo - display differently?


class Data(Defined):

    __slots__ = ()

    def __init__(self, data, state):
        super().__init__('DTA', data, state, data[0] & 0x0f)


class CompressedTimestamp(Defined):

    __slots__ = ()

    def __init__(self, data, state):
        offset = data[0] & 0x1f
        if not state.timestamp:
            raise Exception('Compressed timestamp with no preceding absolute timestamp')
        timestamp = time_to_timestamp(state.timestamp)
        rollover = offset < timestamp & 0x1f
        state.timestamp = timestamp_to_time((timestamp & 0xffffffe0) + offset + (0x20 if rollover else 0))
        super().__init__('DTT', data, state, (data[0] & 0x60) >> 5)

    def parse_token(self, raw_time=False, **options):
        timestamp = time_to_timestamp(self.timestamp) if raw_time else self.timestamp
        if self.definition.timestamp_field:
            extra = {}
        else:
            extra = {'timestamp': ((timestamp,), S)}
        return self.definition.message.parse_message(self.data, self.definition, self.timestamp,
                                                     extra=extra, raw_time=raw_time,
                                                     accumulators=self._accumulators, **options)

    def describe_fields(self, types):
        yield '%s - header (local message type %d - %s; time delta %d)' % \
              (tohex(self.data[0:1]), (self.data[0] & 0x60) >> 5, self.definition.message.name, self.data[0] & 0x1f)
        for field in sorted(self.definition.fields, key=lambda field: field.start):
            if field.name == 'timestamp':
                yield '%s - %s (%s) %s' % (tohex(self.data[field.start:field.finish]), field.name,
                                           field.base_type.name, self.timestamp)
            else:
                yield '%s - %s (%s)' % (tohex(self.data[field.start:field.finish]), field.name, field.base_type.name)

    def repair_timestamp(self, state):
        timestamp = time_to_timestamp(state.timestamp)
        self.data[0] = (self.data[0] & 0xe0) | (timestamp & 0x1f)
        super().repair_timestamp(state)  # any fields too


class Field:

    def __init__(self, size, field, base_type):

        self.size = size
        self.field = field
        self.name = self.field.name if self.field else 'unknown'
        self.base_type = base_type

        self.count = self.size // base_type.n_bytes
        # set by definition later
        self.start = 0
        self.finish = 0


class Definition(Token):

    '''
    Encapsulate the information from the FIT file that selects as Message and a subset of Fields and
    associates them with a particular local_message_type.

    This definition is stored in the state so that when that message type is found it can be used to
    parse the data.
    '''

    def __init__(self, data, state, overhead=6, tag='DFN'):
        self.local_message_type = data[0] & 0x0f
        self.is_user = False
        self.references = set()
        self.timestamp_field = None
        self.endian = data[2] & 0x01
        self.global_message_no = unpack('<>'[self.endian]+'H', data[3:5])[0]
        self.message = state.messages.number_to_message(self.global_message_no)
        self.identity = Identity(self.message.name, state.definition_counter)
        self.fields = self.__process_fields(self._make_fields(data, state), state)
        self.accumulators = state.accumulators
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

    def __process_fields(self, fields, state):
        offset = 1  # header
        fields = tuple(fields)
        for field in fields:
            field.start = offset
            offset += field.size
            field.finish = offset
            if field.field:  # when is this not true?
                field.field.register_accumulator(state.accumulators)
                if field.field.number == TIMESTAMP_GLOBAL_TYPE or field.field.name == 'timestamp_16':
                    self.timestamp_field = field
                if isinstance(field.field, DynamicField):
                    self.references.update(field.field.references)
        self.size = offset
        return tuple(self.__sorted(fields))

    def __provided_by(self, field):
        yield field.name
        if isinstance(field.field, CompositeField):
            for _, component in field.field._components:
                yield component.name

    def __sorted(self, fields):

        by_name = dict((field.name, field) for field in fields)
        names = list(field.name for field in fields)
        providers = defaultdict(list)
        for field in fields:
            for provided in self.__provided_by(field):
                providers[provided].append(field.name)
        references = dict((field.name, field.field.references)
                          for field in fields if isinstance(field.field, DynamicField))

        def follow(name, chain=()):
            if name in chain:
                raise Exception('Circular dependency: %s/%s' % (chain, name))
            chain = chain + (name,)
            for reference in references.get(name, []):
                for provider in providers.get(reference, []):
                    if provider in names:
                        yield from follow(provider, chain=chain)
            names.remove(name)
            yield by_name[name]

        while names:
            yield from follow(names[0])

    def describe_csv(self, record_names=None, field_names=None, internal=False, **options):
        if internal and (not record_names or self.message.name in record_names):
            yield 'Definition'
            yield self.local_message_type
            yield self.message.name
            for field in self.fields:
                if not field_names or field.name in field_names:
                    yield field.name
                    yield field.count
                    yield ''

    def describe_fields(self, types):
        # something of a hack - we pack data in odd places below just to unpack here
        for name, (values, units) in self.parse_token(raw_data=True).data:
            if len(values) > 1:
                (value, extra), padding = values, units
                extra = ': ' + extra
            else:
                value, extra, padding = values[0], '', ''
            value = tohex(value)
            yield '%s%s - %s%s' % (padding, value, sub('_', ' ', name), extra)

    def parse_token(self, raw_data=False, **options):
        data = {'local_message_type': ((self.data[0:1],
                                        str(self.local_message_type)), '') if raw_data else self.local_message_type,
                'reserved': self.data[1:2],
                'architecture': self.data[2:3],
                'message_number': ((self.data[3:5], self.message.name), '') if raw_data else self.global_message_no,
                'no_of_fields': self.data[5:6] if raw_data else self.data[5]}
        if not raw_data:
            data['message_name'] = self.message.name
        for i, field in enumerate(self.fields):
            mult = '' if field.count == 1 else 'x%d' % field.count
            desc = '%s (%s%s)' % (field.name, field.base_type.name, mult)
            raw = self.data[6 + i*3:9 + i*3]
            data['field_%d' % i] = ((raw, desc), '  ') if raw_data else desc
        return self._fake_record('definition', **data)


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
        super().__init__('CRC', False, data)
        self.checksum = unpack('<H', self.data)[0]

    def validate(self, all_data, log, quiet=False):
        checksum = self.crc(all_data[:-2])
        if checksum != self.checksum:
            self._error('Bad checksum (%04x/%04x)' % (checksum, self.checksum), log, quiet)

    def repair(self, data, log):
        checksum = self.crc(data[:-2])
        if checksum != self.checksum:
            log.warning('Fixing final checksum: %04x -> %04x' % (self.checksum, checksum))
            self.checksum = checksum
            self.data[:2] = pack('<H', checksum)

    def parse_token(self, raw_data=False, **options):
        return self._fake_record('checksum', checksum=self.data[0:2] if raw_data else self.checksum)


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
            if header & 0x10:
                log.debug('Reserved bit set')
            token = Data(data, state)
            if token.definition.global_message_no == FIELD_DESCRIPTION:
                return DeveloperField(data, state)
            else:
                return token


class State:

    def __init__(self, types, messages, max_delta_t=None):
        self.types = types
        self.messages = messages
        self.max_delta_t = max_delta_t
        self.dev_fields = defaultdict(lambda: WarnDict(log, 'No definition for developer field %s'))
        self.definitions = WarnDict(log, 'No definition for local message type %s')
        self.definition_counter = Counter()
        self.accumulators = {}
        self._timestamp = None

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, timestamp):
        self._timestamp = self._validate_timestamp(timestamp)

    def _validate_timestamp(self, timestamp):
        if self.max_delta_t and self._timestamp:
            if (timestamp - self._timestamp).total_seconds() > self.max_delta_t:
                raise Exception('Too large shift in timestamp (%.1fs: %s/%s' %
                                ((timestamp - self.timestamp).total_seconds(), self._timestamp, timestamp))
            if timestamp < self._timestamp:
                raise Exception('Timestep decreased (%s/%s)' % (self._timestamp, timestamp))
        return timestamp

    def copy(self):
        copy = State(self.types, self.messages, self.max_delta_t)
        copy.dev_fields.update(self.dev_fields)
        copy.definitions.update(self.definitions)
        copy.definition_counter.update(self.definition_counter)
        copy.accumulators.update(self.accumulators)
        copy._timestamp = self._timestamp
        return copy
