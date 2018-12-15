
from binascii import hexlify


class WarnDict(dict):

    def __init__(self, log, msg):
        self.__log = log
        self.__msg = msg
        super().__init__()

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            msg = self.__msg % (item,)
            self.__log.warn(msg)
            raise KeyError(msg)


class WarnList(list):

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


def tohex(data):
    return hexlify(data).decode('ascii')


def assert_attr(instance, *attrs):
    for attr in attrs:
        if getattr(instance, attr) is None:
            raise Exception('No %s defined' % attr)


class AttrDict(dict):

    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattr__(name)
        else:
            try:
                return self[name]
            except KeyError:
                raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self[name] = value
