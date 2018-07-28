
from abc import abstractmethod
from re import compile
from struct import unpack

import openpyxl as xls
from more_itertools import peekable


LITTLE, BIG = 0, 1


def read_profile(log, path):
    wb = xls.load_workbook(path)
    types = Types(log, wb['Types'])
    messages = Messages(log, wb['Messages'], types)
    return types, messages


class Named:

    def __init__(self, log, name):
        self._log = log
        self.name = name

    def __str__(self):
        return '%s: %s' % (self.__class__.__name__, self.name)


class ErrorDict(dict):

    def __init__(self, log, error_msg):
        self.__log = log
        self.__error_msg = error_msg
        super().__init__()

    def add_named(self, item):
        self[item.name] = item

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            msg = self.__error_msg % item
            self.__log.error(msg)
            raise KeyError(msg)


class AbstractBaseType(Named):

    def __init__(self, log, name, is_base_type=True):
        super().__init__(log, name)
        self.is_base_type = is_base_type

    @abstractmethod
    def profile_to_internal(self, cell_contents):
        pass

    @abstractmethod
    def raw_to_internal(self, bytes, endian):
        pass


class UnimplementedBaseType(AbstractBaseType):
    """
    Helper class for incomplete code during development
    """

    def profile_to_internal(self, cell_contents):
        raise NotImplementedError('%s: %s' % (self.__class__.__name__, self.name))

    def raw_to_internal(self, bytes, endian):
        raise NotImplementedError('%s: %s' % (self.__class__.__name__, self.name))


class InternalBaseType(UnimplementedBaseType):

    def __init__(self, log, name, func):
        super().__init__(log, name)
        self.__func = func

    def profile_to_internal(self, cell_contents):
        if isinstance(cell_contents, int):
            return cell_contents
        else:
            return self.__func(cell_contents)


class StringBaseType(InternalBaseType):

    def __init__(self, log, name):
        super().__init__(log, name, str)


class IntegerBaseType(InternalBaseType):

    def __init__(self, log, name):
        super().__init__(log, name, lambda cell: int(cell, 0))


class BooleanBaseType(InternalBaseType):

    def __init__(self, log, name):
        super().__init__(log, name, bool)


class AutoIntegerBaseType(IntegerBaseType):

    pattern = compile(r'^([su]?)int(\d{1,2})(z?)$')

    size_to_format = {1: 'b', 2: 'h', 4: 'i', 8: 'q'}

    def __init__(self, log, name):
        super().__init__(log, name)
        match = self.pattern.match(name)
        self.signed = match.group(1) != 'u'
        bits = int(match.group(2))
        if bits % 8:
            raise Exception('Size of "%s" not a multiple of 8 bits' % name)
        self.length = bits // 8
        if self.length not in self.size_to_format:
            raise Exception('Cannot unpack %d bytes as an integer' % self.length)
        format = self.size_to_format[self.length]
        self.formats = ['<' + format, '>' + format.upper()]
        self.bad = 0 if match.group(3) == 'z' else 2 ** (bits - 1 if self.signed else 0) - 1

    def raw_to_internal(self, data, endian):
        value = unpack(self.formats[endian], data[0:self.length])[0]
        if value == self.bad:
            value = None
        return self.length, value


class AliasIntegerBaseType(AutoIntegerBaseType):

    def __init__(self, log, name, spec):
        super().__init__(log, spec)
        self.name = name


class AutoFloatBaseType(InternalBaseType):

    def __init__(self, log, name):
        super().__init__(log, name, float)

    pattern = compile(r'^float\d{1,2}$')


class AbstractDefinedType(AbstractBaseType):

    def __init__(self, log, name, base_type):
        super().__init__(log, name, is_base_type=False)
        self.base_type = base_type

    @abstractmethod
    def profile_to_internal(self, cell_contents):
        pass

    @abstractmethod
    def internal_to_profile(self, value):
        pass

    def raw_to_internal(self, bytes):
        return self.base_type.raw_to_internal(bytes)


class MappingType(AbstractDefinedType):

    def __init__(self, log, name, base_type):
        super().__init__(log, name, base_type)
        self._profile_to_internal = ErrorDict(log, 'No internal value for profile "%s"')
        self._internal_to_profile = ErrorDict(log, 'No profile value for internal "%s"')

    def profile_to_internal(self, cell_contents):
        return self._profile_to_internal[cell_contents]

    def internal_to_profile(self, value):
        return self._internal_to_profile[value]


class DefinedType(MappingType):

    def __init__(self, log, row, rows, types):
        name = row[0]
        base_type_name = row[1]
        base_type = types.profile_to_type(base_type_name, auto_create=True)
        if not base_type.is_base_type:
            raise Exception('Base type (%s) for %s is not as bae type' % (base_type_name, name))
        super().__init__(log, name, base_type)
        for row in rows:
            if row[0] or row[2] is None or row[3] is None:
                rows.prepend(row)
                break
            self.__add_mapping(row)
        log.debug('Parsed %d values' % len(self._profile_to_internal))

    def __add_mapping(self, row):
        profile = row[2]
        internal = self.base_type.profile_to_internal(row[3])
        self._profile_to_internal[profile] = internal
        self._internal_to_profile[internal] = profile


class Types:

    def __init__(self, log, sheet):
        self.__log = log
        self.base_type_names = set()
        self.__profile_to_type = ErrorDict(log, 'No type for profile "%s"')
        self.__add_base_types()
        rows = peekable([cell.value for cell in row] for row in sheet.iter_rows())
        for row in rows:
            if row[0] and row[0][0].isupper():
                self.__log.debug('Skipping %s' % row)
            elif row[0]:
                self.__log.info('Parsing type %s' % row[0])
                self.__profile_to_type.add_named(DefinedType(self.__log, row, rows, self))

    def __add_base_types(self):
        self.__add_base_type(StringBaseType(self.__log, 'string'))
        self.__add_base_type(IntegerBaseType(self.__log, 'enum'))
        self.__add_base_type(AliasIntegerBaseType(self.__log, 'byte', 'uint8'))  # todo array
        self.__add_base_type(BooleanBaseType(self.__log, 'bool'))

    def __add_base_type(self, type):
        if not type.is_base_type:
            raise Exception('Bad base type "%s"' % type)
        self.base_type_names.add(type.name)
        self.__profile_to_type.add_named(type)

    def profile_to_type(self, name, auto_create=False):
        try:
            return self.__profile_to_type[name]
        except KeyError:
            if auto_create:
                for cls in (AutoFloatBaseType, AutoIntegerBaseType):
                    match = cls.pattern.match(name)
                    if match:
                        self.__log.warn('Auto-adding base type %s for "%s"' % (cls.__name__, name))
                        self.__add_base_type(cls(self.__log, name))
                        return self.profile_to_type(name)
            raise


class MessageField:

    def __init__(self, log, name, number, type):
        self._log = log
        self.name = name
        self.number = number
        self.is_dynamic = self.number is None
        self.type = type

    def profile_to_internal(self, name):
        return self.type.profile_to_internal(name)

    def raw_to_internal(self, data, endian):
        if self.is_dynamic:
            raise NotImplementedError()
        offset, value = self.type.raw_to_internal(data, endian)
        return offset, self.name, value


class RowMessageField(MessageField):

    def __init__(self, log, row, types):
        super().__init__(log, row[2],
                         int(row[1]) if row[1] else None,
                         types.profile_to_type(row[3], auto_create=True))


class DynamicMessageField(RowMessageField):

    def __init__(self, log, row, rows, types):
        super().__init__(log, row, types)
        self.__dynamic_tmp_data = []
        self.__dynamic_lookup = ErrorDict(log, 'No dynamic field for "%s"')
        self.references = set()
        try:
            peek = rows.peek()
            while peek[2] and peek[1] is None:
                row = next(rows)
                for name, value in zip(row[11].split(','), row[12].split(',')):
                    self.__save_dynamic(name.strip(), value.strip(), row)
                peek = rows.peek()
        except StopIteration:
            return

    def __save_dynamic(self, reference_name, reference_value, row):
        self.is_dynamic = True
        self.__dynamic_tmp_data.append((reference_name, reference_value, row))

    def _complete_dynamic(self, message, types):
        for reference_name, reference_value, row in self.__dynamic_tmp_data:
            reference = message.profile_to_field(reference_name)
            value = reference.profile_to_internal(reference_value)
            self.references.add(reference)
            self.__dynamic_lookup[(reference_name, value)] = RowMessageField(self._log, row, types)

    @property
    def dynamic(self):
        return self.__dynamic_lookup


class AbstractMessage(Named):

    def __init__(self, log, name):
        super().__init__(log, name)
        self._profile_to_field = ErrorDict(log, 'No field for profile "%s"')
        self._number_to_field = ErrorDict(log, 'No field for  internal "%s"')

    def _add_field(self, field):
        self._profile_to_field.add_named(field)
        self._number_to_field[field.number] = field

    def profile_to_field(self, name):
        return self._profile_to_field[name]

    def number_to_field(self, value):
        return self._number_to_field[value]

    def raw_to_internal(self, data, numbers, endian):
        offset = 0
        message = {}
        for number in numbers:
            field = self.number_to_field(number)
            delta, name, value = field.raw_to_internal(data[offset:], endian)
            message[name] = value
            offset += delta
        return offset, message


class RowMessage(AbstractMessage):

    def __init__(self, log, row, rows, types):
        super().__init__(log, row[0])
        for row in rows:
            if not row[2]:
                rows.prepend(row)
                break
            self.__parse_row(row, rows, types)
        self.__complete_dynamic(types)

    def __parse_row(self, row, rows, types):
        self._add_field(DynamicMessageField(self._log, row, rows, types))

    def __complete_dynamic(self, types):
        # these may be forward references
        for data in self._profile_to_field.values():
            if data.is_dynamic:
                data._complete_dynamic(self, types)


class Header(AbstractMessage):

    def __init__(self, log, types):
        super().__init__(log, 'HEADER')
        self._add_field(MessageField(log, 'header_size', 0, types.profile_to_type('uint8')))
        self._add_field(MessageField(log, 'protocol_version', 1, types.profile_to_type('uint8')))
        self._add_field(MessageField(log, 'profile_version', 2, types.profile_to_type('uint16', auto_create=True)))
        self._add_field(MessageField(log, 'data_size', 3, types.profile_to_type('uint32', auto_create=True)))
        self._add_field(MessageField(log, 'fit_text', 4, types.profile_to_type('uint64', auto_create=True)))  # todo array of byte
        self._add_field(MessageField(log, 'checksum', 5, types.profile_to_type('uint16', auto_create=True)))

    def raw_to_internal(self, data, numbers=None, endian=LITTLE):
        if numbers is None:
            offset, message = super().raw_to_internal(data, (0,), endian)
            if message['header_size'] == 12:
                numbers = tuple(range(5))
            else:
                numbers = tuple(range(6))
        return super().raw_to_internal(data, numbers, endian)


class Messages:

    def __init__(self, log, sheet, types):
        self.__log = log
        self.__profile_to_message = ErrorDict(log, 'No message for profile "%s"')
        rows = peekable([cell.value for cell in row] for row in sheet.iter_rows())
        for row in rows:
            if row[0] and row[0][0].isupper():
                self.__log.debug('Skipping %s' % row)
            elif row[0]:
                self.__log.info('Parsing message %s' % row[0])
                self.__profile_to_message.add_named(RowMessage(self.__log, row, rows, types))
        self.__profile_to_message.add_named(Header(self.__log, types))

    def profile_to_message(self, name):
        return self.__profile_to_message[name]
