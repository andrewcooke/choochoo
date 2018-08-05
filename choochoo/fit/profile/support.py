from collections.__init__ import namedtuple


class NullableLog:

    def __init__(self, log):
        self.__log = log

    def set_log(self, log):
        self.__log = log

    def debug(self, *args):
        self.__log.debug(*args)

    def info(self, *args):
        self.__log.info(*args)

    def warn(self, *args):
        self.__log.warn(*args)

    def error(self, *args):
        self.__log.error(*args)


class Named:
    """
    Has a name.  Base for both fields and messages
    """

    def __init__(self, log, name):
        self._log = log
        self.name = name

    def __str__(self):
        return '%s: %s' % (self.__class__.__name__, self.name)


class ErrorDict(dict):

    def __init__(self, log, msg):
        self.__log = log
        self.__msg = msg
        super().__init__()

    def add_named(self, item):
        self[item.name] = item

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            msg = self.__msg % (item,)
            self.__log.warn(msg)
            raise KeyError(msg)


class ErrorList(list):

    def __init__(self, log, msg):
        self.__log = log
        self.__msg = msg
        super().__init__()

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except IndexError:
            msg = self.__msg % item
            self.__log.warn(msg)
            raise IndexError(msg)


class Row(namedtuple('BaseRow',
                     'msg_name, field_no_, field_name, field_type, array, components, scale, offset, ' +
                     'units, bits_, accumulate_, ref_name, ref_value, comment, products, example')):

    __slots__ = ()

    def __new__(cls, row):
        return super().__new__(cls, *tuple(cell.value for cell in row[0:16]))

    @property
    def field_no(self):
        return None if self.field_no_ is None else int(self.field_no_)

    @property
    def bits(self):
        return None if self.bits_ is None else str(self.bits_)

    @property
    def accumulate(self):
        return None if self.accumulate_ is None else str(self.accumulate_)
