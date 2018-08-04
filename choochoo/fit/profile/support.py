

class NullableLog:

    def __init__(self, log):
        self.set_log(log)

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
            msg = self.__error_msg % (item,)
            self.__log.error(msg)
            raise KeyError(msg)


class ErrorList(list):

    def __init__(self, log, error_msg):
        self.__log = log
        self.__error_msg = error_msg
        super().__init__()

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except IndexError:
            msg = self.__error_msg % item
            self.__log.error(msg)
            raise IndexError(msg)