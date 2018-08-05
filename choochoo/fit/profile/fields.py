from itertools import repeat

from .support import Named, ErrorDict


TIMESTAMP_GLOBAL_TYPE = 253


class SimpleMessageField(Named):

    def __init__(self, log, name, number, units, type, scale=1, offset=0, accumulate=False):
        super().__init__(log, name)
        self.number = number  # public for indexing in message
        self.__units = units if units else ''
        self.is_dynamic = False  # public because need to delay evaluation (order fields)
        self._is_component = False
        self.type = type  # public for Field (in Definition) base type
        self.__scale = self.__parse_int(scale, 1, name)
        self.__offset = self.__parse_int(offset, 0, name)
        self.__is_scaled = (self.__scale != 1 or self.__offset != 0)
        self.__is_accumulate = self.__parse_int(accumulate, 0, name)

    def __parse_int(self, cell, default, name):
        if cell is None or cell == '':
            return default
        try:
            return int(cell)
        except:
            self._log.warn('Could not parse %r for %s (scale/offset)' % (cell, name))
            return default

    def parse(self, data, count, endian, references, accumulate, message):
        values = self.type.parse(data, count, endian)
        if values is not None:
            if self.__is_scaled:
                values = tuple(value / self.__scale - self.__offset for value in values)
            if self.__is_accumulate:
                values = accumulate(self, values)
        yield self.name, (values, self.__units)


class ComponentMessageField(SimpleMessageField):

    def _zip(self, *fields):
        return zip(*(self.__split(field, extend=n > 1) for n, field in enumerate(fields)))

    def __split(self, field, extend=False):
        if field:
            for value in str(field).split(','):
                yield value.strip()
        else:
            yield None
        if extend:
            self._log.warn('Extending field')
            yield from repeat(None)

    def __init__(self, log, row, types):
        super().__init__(log, row.field_name, row.field_no, row.units,
                         types.profile_to_type(row.field_type, auto_create=True),
                         None if row.components else row.scale,
                         None if row.components else row.offset,
                         None if row.components else row.accumulate)
        self.__components = []
        if row.components:
            for (name, bits, accumulate, scale, offset) in \
                    self._zip(row.components, row.bits, row.accumulate, row.scale, row.offset):
                if accumulate or scale or offset:
                    print(accumulate)
                self._is_component = True
                self.__components.append((int(bits), name))

    def parse(self, data, count, endian, references, accumulate, message):
        if self._is_component:
            byteorder = ['little', 'big'][endian]
            bits = int.from_bytes(data, byteorder=byteorder)
            for nbits, name in self.__components:
                field = message.profile_to_field(name)
                nbytes = max((nbits+7) // 8, field.type.size)
                data = (bits & ((1 << bits) - 1)).to_bytes(nbytes, byteorder=byteorder)
                bits >>= nbits
                yield from field.parse(data, 1, endian, references, accumulate, message)
            return
        yield from super().parse(data, count, endian, references, accumulate, message)


class DynamicMessageField(ComponentMessageField):

    def __init__(self, log, row, rows, types):
        super().__init__(log, row, types)
        self.__dynamic_lookup = ErrorDict(log, 'No dynamic field for %r')
        self.references = set()
        peek = rows.peek()
        while peek and peek.field_name and peek.field_no is None:
            row = next(rows)
            for name, value in self._zip(row.ref_name, row.ref_value):
                self.is_dynamic = True
                self.references.add(name)
                self.__dynamic_lookup[(name, value)] = ComponentMessageField(self._log, row, types)
            peek = rows.peek()

    @property
    def dynamic(self):
        return self.__dynamic_lookup

    def parse(self, data, count, endian, references, accumulate, message):
        if self.is_dynamic:
            for name in self.references:
                if name in references:
                    value = references[name][0][0]  # drop units and take first value
                    try:
                        yield from self.dynamic[(name, value)].parse(
                            data, count, endian, references, accumulate, message)
                        return
                    except KeyError:
                        pass
            # self._log.warn('No match for dynamic field %s (message %s)' % (self.name, message.name))
            # and if nothing found, fall though to default behaviour
        yield from super().parse(data, count, endian, references, accumulate, message)
