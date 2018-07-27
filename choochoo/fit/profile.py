
from abc import abstractmethod
from collections import Mapping
from re import compile

import openpyxl as xls
from more_itertools import peekable


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


class ReadOnlyDict(Mapping):

    def __init__(self, log, error_msg):
        self._log = log
        self.__error_msg = error_msg
        self.__data = {}

    def add(self, name, value):
        self.__data[name] = value

    def add_named(self, item):
        self.add(item.name, item)

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


class AbstractBaseType(Named):

    def __init__(self, log, name, is_base_type=True):
        super().__init__(log, name)
        self.is_base_type = is_base_type

    @abstractmethod
    def profile_to_internal(self, cell_contents):
        pass

    @abstractmethod
    def raw_to_internal(self, bytes):
        pass


class UnimplementedBaseType(AbstractBaseType):
    """
    Helper class for incomplete code during development
    """

    def profile_to_internal(self, cell_contents):
        raise NotImplemented()

    def raw_to_internal(self, bytes):
        raise NotImplemented()


class StringBaseType(UnimplementedBaseType):

    def profile_to_internal(self, cell_contents):
        return str(cell_contents)


class IntegerBaseType(UnimplementedBaseType):

    def profile_to_internal(self, cell_contents):
        if isinstance(cell_contents, int):
            return cell_contents
        else:
            return int(cell_contents, 0)


class BooleanBaseType(UnimplementedBaseType):

    pass


class AutoIntegerBaseType(IntegerBaseType):

    pattern = compile(r'^[su]?int\d{1,2}z?$')


class AutoFloatBaseType(IntegerBaseType):

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
        self._profile_to_internal = ReadOnlyDict(log, 'No internal value for profile "%s"')
        self._internal_to_profile = ReadOnlyDict(log, 'No profile value for internal "%s"')

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
        self._profile_to_internal.add(profile, internal)
        self._internal_to_profile.add(internal, profile)


class Types:

    def __init__(self, log, sheet):
        self.__log = log
        self.base_type_names = set()
        self.__profile_to_type = ReadOnlyDict(log, 'No type for profile "%s"')
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
        self.__add_base_type(IntegerBaseType(self.__log, 'byte'))
        self.__add_base_type(BooleanBaseType(self.__log, 'bool'))

    def __add_base_type(self, type):
        if not type.is_base_type:
            raise Exception('Bad base type "%s"' % type)
        self.base_type_names.add(type.name)
        self.__profile_to_type.add(type.name, type)

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


class SimpleMessageField:

    def __init__(self, log, row, types):
        self._log = log
        self.name = row[2]
        self.number = int(row[1]) if row[1] else None
        self.is_dynamic = self.number is None
        self.type = types.profile_to_type(row[3], auto_create=True)

    def profile_to_internal(self, name):
        return self.type.profile_to_internal(name)


class MessageField(SimpleMessageField):

    def __init__(self, log, row, rows, types):
        super().__init__(log, row, types)
        self.__dynamic_tmp_data = []
        self.__dynamic_lookup = ReadOnlyDict(log, 'No dynamic field for "%s"')
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
            self.__dynamic_lookup.add((reference_name, value), SimpleMessageField(self._log, row, types))

    @property
    def dynamic(self):
        return self.__dynamic_lookup


class Message(Named):

    def __init__(self, log, row, rows, types):
        super().__init__(log, row[0])
        self.__profile_to_field = ReadOnlyDict(log, 'No field for profile "%s"')
        self.__internal_to_field = ReadOnlyDict(log, 'No field for  internal "%s"')
        for row in rows:
            if not row[2]:
                rows.prepend(row)
                break
            self.__add_field(row, rows, types)
        self.__complete_dynamic(types)

    def __add_field(self, row, rows, types):
        field = MessageField(self._log, row, rows, types)
        self.__profile_to_field.add_named(field)
        self.__internal_to_field.add(field.number, field)

    def __complete_dynamic(self, types):
        # these may be forward references
        for data in self.__profile_to_field.values():
            if data.is_dynamic:
                data._complete_dynamic(self, types)

    def profile_to_field(self, name):
        return self.__profile_to_field[name]

    def internal_to_field(self, value):
        return self.__internal_to_field[value]


class Messages:

    def __init__(self, log, sheet, types):
        self.__log = log
        self.__profile_to_message = ReadOnlyDict(log, 'No message for profile "%s"')
        rows = peekable([cell.value for cell in row] for row in sheet.iter_rows())
        for row in rows:
            if row[0] and row[0][0].isupper():
                self.__log.debug('Skipping %s' % row)
            elif row[0]:
                self.__log.info('Parsing message %s' % row[0])
                self.__profile_to_message.add_named(Message(self.__log, row, rows, types))

    def profile_to_message(self, name):
        return self.__profile_to_message[name]