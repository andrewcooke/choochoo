
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
