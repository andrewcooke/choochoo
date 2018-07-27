
from collections import Mapping

import openpyxl as x
from more_itertools import peekable


def read_profile(log, path):
    wb = x.load_workbook(path)
    types = Types(log, wb['Types'])
    messages = Messages(log, wb['Messages'], types)
    return types, messages


class ReadOnlyDict(Mapping):

    def __init__(self, log, error_msg):
        self._log = log
        self.__error_msg = error_msg
        self.__data = {}

    def _add(self, name, value):
        self.__data[name] = value

    def __getitem__(self, item):
        try:
            return self.__data[item]
        except KeyError:
            msg = self.__error_msg % item
            self._log.error(msg)
            raise KeyError(msg)

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)


class NamedDict(ReadOnlyDict):

    def __init__(self, log, error_msg, name):
        super().__init__(log, error_msg)
        self.name = name


class Type(NamedDict):

    def __init__(self, log, name, base, rows):
        super().__init__(log, 'No value for "%s"', name)
        self.base_type = base
        self.__comments = ReadOnlyDict(self._log, 'No comment for "%s"')
        for row in rows:
            if row[0] or not row[2]:
                rows.prepend(row)
                return
            self.__parse(row)

    def __parse(self, row):
        name = row[2]
        if isinstance(row[3], int):
            value = row[3]
        else:
            try:
                value = int(row[3], 0)
            except TypeError:
                self.__log.error('Cannot parse value "%s" (type %s)' % (row[3], type(row[3])))
                raise
        self._add(name, value)
        self._add(value, name)


class Types(ReadOnlyDict):

    def __init__(self, log, sheet):
        super().__init__(log, 'No type for "%s"')
        self.base_types = set()
        rows = peekable([cell.value for cell in row] for row in sheet.iter_rows())
        for row in rows:
            if row[0] and row[0][0].isupper():
                self._log.debug('Skipping %s' % row)
            elif row[0]:
                self._log.info('Parsing type %s' % row[0])
                self.base_types.add(row[1])
                self._add(row[0], Type(self._log, row[0], row[1], rows))


class SimpleMessageField:

    def __init__(self, log, name, number, row, types):
        self._log = log
        self.name = name
        self.number = number
        self.type_name = row[3]
        try:
            self.type = types[self.type_name]
            self.is_base_type = False
        except KeyError:
            if type not in types.base_types:
                self._log.warn('Additional base type: %s' % type)
                types.base_types.add(type)
            self.is_base_type = True

    def parse(self, value):
        if self.is_base_type:
            if self.type_name == 'string':
                return value
            elif 'int' in self.type_name:
                return int(value, 0)
            else:
                return float(value)
        else:
            return self.type[value]


class MessageField(SimpleMessageField):

    def __init__(self, log, name, number, row, rows, types):
        super().__init__(log, name, number, row, types)
        self.is_dynamic = False
        self.__dynamic_store = []
        self.dynamic = ReadOnlyDict(self._log, 'No dynamic match for "%s"')
        self.dynamic_fields = set()
        try:
            peek = rows.peek()
            while peek[2] and peek[1] is None:
                row = next(rows)
                for name, value in zip(row[11].split(','), row[12].split(',')):
                    self.__store_dynamic(name.strip(), value.strip(), row)
                peek = rows.peek()
        except StopIteration:
            return

    def __store_dynamic(self, dynamic_name, dynamic_value, row):
        self.is_dynamic = True
        self.__dynamic_store.append((dynamic_name, dynamic_value, row))

    def _complete_dynamic(self, message, types):
        for dynamic_name, dynamic_value, row in self.__dynamic_store:
            field = message[dynamic_name]
            value = field.parse(dynamic_value)
            self.dynamic_fields.add(field)
            self.dynamic._add((dynamic_name, value), SimpleMessageField(self._log, row[2], None, row, types))


class Message(NamedDict):

    def __init__(self, log, name, rows, types):
        super().__init__(log, 'No field for "%s"', name)
        for row in rows:
            if not row[2]:
                rows.prepend(row)
                break
            self.__parse(row, rows, types)
        self.__complete_dynamic(types)

    def __parse(self, row, rows, types):
        number = int(row[1])
        name = row[2]
        data = MessageField(self._log, name, number, row, rows, types)
        self._add(name, data)
        self._add(number, data)

    def __complete_dynamic(self, types):
        # these may be forward references
        for data in self.values():
            if data.is_dynamic:
                data._complete_dynamic(self, types)


class Messages(ReadOnlyDict):

    def __init__(self, log, sheet, types):
        super().__init__(log, 'No message for "%s"')
        self.__messages = {}
        rows = peekable([cell.value for cell in row] for row in sheet.iter_rows())
        for row in rows:
            if row[0] and row[0][0].isupper():
                self._log.debug('Skipping %s' % row)
            elif row[0]:
                self._log.info('Parsing message %s' % row[0])
                self._add(row[0], Message(self._log, row[0], rows, types))
