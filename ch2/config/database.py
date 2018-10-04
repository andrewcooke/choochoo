
from ..command.args import parser, NamespaceWithVariables, NO_OP
from ..lib.log import make_log
from ..squeal.database import Database


def config(*args):
    '''
    Start here to configure the system.  Create an instance on the command line:

        log, db = config('-v', '4')
        print(c...)  todo
        ...
    '''
    p = parser()
    args = list(args)
    args.append(NO_OP)
    ns = NamespaceWithVariables(p.parse_args(args))
    log = make_log(ns)
    db = Database(ns, log)
    return log, db


def add(session, instance):
    session.add(instance)
    return instance


class Counter:

    def __init__(self, start=10, delta=10):
        self.__start = start
        self.__delta = delta
        self.__previous = None

    def __call__(self, reset=None, delta=None):
        if delta is not None:
            if delta < 1:
                raise Exception('Negative increment')
            self.__delta = delta
        if reset is None:
            if self.__previous is None:
                self.__previous = self.__start
            else:
                self.__previous += self.__delta
        else:
            if reset <= self.__previous:
                raise Exception('Sort not increasing with reset')
            else:
                self.__previous = reset
        return self.__previous
