
from .support import Named, ErrorDict


TIMESTAMP_GLOBAL_TYPE = 253


def parse_scale_offset(log, cell, default, name):
    if cell is None or cell == '':
        return default
    try:
        return int(cell)
    except:
        log.warn('Could not parse %r for %s (scale/offset)' % (cell, name))
        return default


class SimpleMessageField(Named):

    def __init__(self, log, name, number, units, type, count=None, scale=1, offset=0):
        super().__init__(log, name)
        self.number = number
        self.units = units if units else ''
        self.is_dynamic = False
        self.is_component = False
        self.type = type
        self.count = count
        self.scale = parse_scale_offset(log, scale, 1, name)
        self.offset = parse_scale_offset(log, offset, 0, name)
        self.__is_scaled = (self.scale != 1 or self.offset != 0)

    def parse(self, data, count, endian, result, message):
        values = self.type.parse(data, count, endian)
        if self.__is_scaled and values is not None:
            values = tuple(value / self.scale - self.offset for value in values)
        yield self.name, (values, self.units)


class ComponentMessageField(SimpleMessageField):

    @staticmethod
    def _zip(field1, field2):
        return ((f1.strip(), f2.strip()) for f1, f2 in zip(field1.split(','), field2.split(',')))

    def __init__(self, log, row, types):
        super().__init__(log, row.field_name, row.field_no,
                         row.units,
                         types.profile_to_type(row.field_type, auto_create=True),
                         row.example, row.scale, row.offset)
        if row.components:
            self.__components = []
            for (name, bits) in self._zip(row.components, row.bits):
                self.is_component = True
                self.__components.append((int(bits), name))


class DynamicMessageField(ComponentMessageField):

    def __init__(self, log, row, rows, types):
        super().__init__(log, row, types)
        self.__dynamic_tmp_data = []
        self.__dynamic_lookup = ErrorDict(log, 'No dynamic field for %r')
        self.references = set()
        try:
            peek = rows.peek()
            while peek.field_name and peek.field_no is None:
                row = next(rows)
                for name, value in self._zip(row.ref_name, row.ref_value):
                    self.is_dynamic = True
                    self.references.add(name)
                    self.__dynamic_lookup[(name, value)] = DynamicMessageField(self._log, row, rows, types)
                peek = rows.peek()
        except StopIteration:
            return

    @property
    def dynamic(self):
        return self.__dynamic_lookup

    def parse(self, data, count, endian, result, message):
        if self.is_dynamic:
            for name in self.references:
                if name in result:
                    value = result[name][0][0]  # drop units and take first value
                    self._log.debug('Found reference %r=%r' % (name, value))
                    try:
                        yield from self.dynamic[(name, value)].parse(data, count, endian, result, message)
                        return
                    except KeyError:
                        pass
            # self._log.warn('No match for dynamic field %s (message %s)' % (self.name, message.name))
            # and if nothing found, fall though to default behaviour
        yield from super().parse(data, count, endian, result, message)