
from .fields import Row, MessageField, TypedField
from .support import Named
from .support import Rows
from ..records import LazyRecord
from ...lib.data import WarnDict

HEADER_GLOBAL_TYPE = -1

HEADER_FIELDS = [
    ('header_size', 1, 'uint8'),
    ('protocol_version', 1, 'uint8'),
    ('profile_version', 1, 'uint16'),
    ('data_size', 1, 'uint32'),
    ('fit_text', 4, 'string'),
    ('checksum', 1, 'uint16')
]


class Message(Named):

    def __init__(self, log, name, number=None):
        super().__init__(log, name)
        self.number = number
        self._profile_to_field = WarnDict(log, 'No field for profile %r')
        self._number_to_field = WarnDict(log, 'No field for number %r')

    def _add_field(self, field):
        self._profile_to_field.add_named(field)
        self._number_to_field[field.number] = field

    def profile_to_field(self, name):
        return self._profile_to_field[name]

    def number_to_field(self, value):
        return self._number_to_field[value]

    def parse(self, data, defn, timestamp=None):
        return LazyRecord(self.name, self.number, defn.identity, timestamp, self.__parse(data, defn))

    def __parse(self, data, defn):
        # this is the generator that lives inside a record and is evaluated on demand
        references = {} if defn.references else None
        for field in defn.fields:
            bytes = data[field.start:field.finish]
            if field.field:
                for name, value in self._parse_field(
                        field.field, bytes, field.count, defn.endian, references, defn.accumulate, self):
                    if name in defn.references:
                        references[name] = value
                    yield name, value
            else:
                name = '@%d:%d' % (field.start, field.finish)
                value = (field.base_type.parse(bytes, field.count, defn.endian), None)
                if name in defn.references:
                    references[name] = value
                yield name, value

    def _parse_field(self, field, bytes, count, endian, references, accumulate, message):
        # allow interception for optional field in header
        yield from field.parse(bytes, count, endian, references, accumulate, message)


class RowMessage(Message):

    def __init__(self, log, row, rows, types):
        try:
            number = types.profile_to_type('mesg_num').profile_to_internal(row.msg_name)
        except KeyError:
            number = None
            log.warn('No mesg_num for %r' % name)
        super().__init__(log, row.msg_name, number)
        while rows:
            if not rows.peek().field_name:
                break
            self._add_field(MessageField(self._log, next(rows), rows, types))


class Header(Message):

    def __init__(self, log, types):
        super().__init__(log, 'HEADER', number=HEADER_GLOBAL_TYPE)
        for n, (name, size, base_type) in enumerate(HEADER_FIELDS):
            self._add_field(TypedField(log, name, n, None, None, None, None, base_type, types))

    def _parse_field(self, field, data, count, endian, references, accumulate, message):
        if field.name == 'checksum' and references['header_size'] == 12:
            yield None, None
        else:
            yield from super()._parse_field(field, data, count, endian, references, accumulate, message)


class Missing(Message):

    def __init__(self, log, number):
        super().__init__(log, 'MESSAGE %d' % number, number)


class Messages:

    def __init__(self, log, sheet, types):
        self.__log = log
        self.__profile_to_message = WarnDict(log, 'No message for profile %r')
        self.__number_to_message = WarnDict(log, 'No message for number %r')
        rows = Rows(sheet, wrapper=Row)
        for row in rows:
            if row.msg_name and row.msg_name[0].isupper():
                self.__log.debug('Skipping %s' % (row,))
            elif row.msg_name:
                # self.__log.info('Parsing message %s' % row.msg_name)
                self.__add_message(RowMessage(self.__log, row, rows, types))
        self.__add_message(Header(self.__log, types))

    def __add_message(self, message):
        self.__profile_to_message.add_named(message)
        try:
            self.__number_to_message[message.number] = message
        except AttributeError:
            pass

    def profile_to_message(self, name):
        return self.__profile_to_message[name]

    def number_to_message(self, number):
        try:
            return self.__number_to_message[number]
        except KeyError:
            message = Missing(self.__log, number)
            self.__number_to_message[number] = message
            return message


