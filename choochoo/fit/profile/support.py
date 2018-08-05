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


class Rows:

    def __init__(self, sheet, wrapper=tuple):
        self.__rows = (wrapper(cell.value for cell in row) for row in sheet.iter_rows())
        self.__next = None

    def __next__(self):
        if self.__next:
            value, self.__next = self.__next, None
        else:
            value = next(self.__rows)
        return value

    def __iter__(self):
        return self

    def __bool__(self):
        return bool(self.peek())

    def peek(self):
        if not self.__next:
            try:
                self.__next = next(self.__rows)
                return self.__next
            except StopIteration:
                pass
        return self.__next

