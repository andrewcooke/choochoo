
from .fields import Row, MessageField, TypedField
from .support import Named
from .support import Rows
from ..format.records import LazyRecord
from ...lib.data import WarnDict

'''
A message is a collection of fields, as defined in the Profile document.

During parsing Definition instances are created which associated a Message with a subset of Fields.

Then, when the Token associated with the Definition is read and needs to be parsed, the Token delegates
the work to the Definition, which in turn delegates the work to the Message, which in turn delegates to 
the Field(s).
'''


class Message(Named):

    def __init__(self, log, name, number=None, warn=False):
        super().__init__(log, name)
        self.number = number
        self._profile_to_field = WarnDict(log, 'No field for profile %r') if warn else dict()
        self._number_to_field = WarnDict(log, 'No field for number %r') if warn else dict()

    def _add_field(self, field):
        self._profile_to_field[field.name] = field
        self._number_to_field[field.number] = field

    def profile_to_field(self, name):
        return self._profile_to_field[name]

    def number_to_field(self, value):
        return self._number_to_field[value]

    def _post(self, types):
        for field in self._number_to_field.values():
            field.post(self, types)

    def parse_message(self, data, defn, timestamp, extra=None, **options):
        return LazyRecord(self.name, self.number, defn.identity, timestamp,
                          self.__parse(data, defn, timestamp, extra=extra, **options))

    def __parse(self, data, defn, timestamp, extra=None, **options):
        # this is the generator that lives inside a record and is evaluated on demand
        if extra is None: extra = {}
        references = {}
        for name, value in extra.items():
            if name in defn.references and value[0] is not None:
                references[name] = value
            yield name, value
        for field in defn.fields:
            bytes = data[field.start:field.finish]
            if field.field:
                for name, value in self._parse_field(
                        field.field, bytes, field.count, defn.endian, timestamp, references, self, **options):
                    if name in defn.references and value[0] is not None:
                        references[name] = value
                    yield name, value
            else:
                name = '@%d:%d' % (field.start, field.finish)
                value = (field.base_type.parse_type(bytes, field.count, defn.endian, timestamp), None)
                yield name, value

    def _parse_field(self, field, bytes, count, endian, timestamp, references, message, **options):
        # allow interception for optional field in header
        yield from field.parse_field(bytes, count, endian, timestamp, references, message, **options)


class RowMessage(Message):

    def __init__(self, log, row, rows, types, warn=False):
        number = types.profile_to_type('mesg_num').profile_to_internal(row.msg_name)
        super().__init__(log, row.msg_name, number, warn=warn)
        while rows:
            if not rows.peek().field_name:
                self._post(types)
                break
            self._add_field(MessageField(self._log, next(rows), rows, types))


class Missing(Message):

    def __init__(self, log, number):
        super().__init__(log, 'MESSAGE %d' % number, number)


class Messages:

    def __init__(self, log, sheet, types, warn=False):
        self.__log = log
        self.__profile_to_message = WarnDict(log, 'No message for profile %r') if warn else dict()
        self.__number_to_message = WarnDict(log, 'No message for number %r') if warn else dict()
        rows = Rows(sheet, wrapper=Row)
        for row in rows:
            if row.msg_name and row.msg_name[0].isupper():
                self.__log.debug('Skipping %s' % (row,))
            elif row.msg_name:
                # self.__log.info('Parsing message %s' % row.msg_name)
                self.__add_message(RowMessage(self.__log, row, rows, types, warn=warn))

    def __add_message(self, message):
        self.__profile_to_message[message.name] = message
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


