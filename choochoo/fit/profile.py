
from collections import Mapping

import openpyxl as x
from more_itertools import peekable


def read_profile(log, path):
    wb = x.load_workbook(path)
    types = Types(log, wb['Types'])
    messages = Messages(log, wb['Messages'], types)
    return types, messages


class ReadOnlyDict(Mapping):

    def __init__(self, log):
        self._log = log
        self.__data = {}

    def _add(self, name, value):
        self.__data[name] = value

    def __getitem__(self, item):
        return self.__data[item]

    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)


class NamedDict(ReadOnlyDict):

    def __init__(self, log, name):
        super().__init__(log)
        self.name = name


class Type(NamedDict):

    def __init__(self, log, name, base, rows):
        super().__init__(log, name)
        self.base_type = base
        self.__comments = {}
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
                self._log.error('Cannot parse value "%s" (type %s)' % (row[3], type(row[3])))
                raise
        self._add(name, value)
        self._add(value, name)


class Types(ReadOnlyDict):

    def __init__(self, log, sheet):
        super().__init__(log)
        self.base_types = set()
        rows = peekable([cell.value for cell in row] for row in sheet.iter_rows())
        for row in rows:
            if row[0] and row[0][0].isupper():
                self._log.debug('Skipping %s' % row)
            elif row[0]:
                self._log.info('Parsing type %s' % row[0])
                self.base_types.add(row[1])
                self._add(row[0], Type(self._log, row[0], row[1], rows))


class MessageData:

    def __init__(self, log, name, number, row, rows, types):
        self._log = log
        self.name = name
        self.number = number
        type = row[3]
        try:
            self.type = types[type]
            self.is_base_type = False
        except KeyError:
            if type not in types.base_types:
                self._log.warn('Additional base type: %s' % type)
                types.base_types.add(type)
            self.is_base_type = True
        # drop dynamic for now
        try:
            peek = rows.peek()
            while peek[2] and not peek[1]:
                self._log.warn('Skipping %s' % next(rows))
                peek = rows.peek()
        except StopIteration:
            return


class Message(NamedDict):

    def __init__(self, log, name, rows, types):
        super().__init__(log, name)
        for row in rows:
            if not row[2]:
                rows.prepend(row)
                return
            self.__parse(row, rows, types)

    def __parse(self, row, rows, types):
        number = int(row[1])
        name = row[2]
        data = MessageData(self._log, name, number, row, rows, types)
        self._add(name, data)
        self._add(number, data)


class Messages(ReadOnlyDict):

    def __init__(self, log, sheet, types):
        super().__init__(log)
        self.__messages = {}
        rows = peekable([cell.value for cell in row] for row in sheet.iter_rows())
        for row in rows:
            if row[0] and row[0][0].isupper():
                self._log.debug('Skipping %s' % row)
            elif row[0]:
                self._log.info('Parsing message %s' % row[0])
                self._add(row[0], Message(self._log, row[0], rows, types))
