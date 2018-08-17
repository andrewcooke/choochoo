
from argparse import ArgumentParser
from genericpath import exists
from os import makedirs
from os.path import dirname, expanduser, realpath, normpath, relpath, join
from re import compile, sub
from typing import Mapping

PROGNAME = 'ch2'
COMMAND = 'command'
TOPIC = 'topic'

DIARY = 'diary'
DUMP_FIT = 'dump-fit'
HELP = 'help'
INJURIES = 'injuries'
PACKAGE_FIT_PROFILE = 'package-fit-profile'
PLAN = 'plan'
SCHEDULES = 'schedules'
V, VERBOSITY = 'v', 'verbosity'
VERSION = 'version'

AFTER = 'after'
ALL_MESSAGES = 'all-messages'
ALL_FIELDS = 'all-fields'
DATABASE = 'database'
DEV = 'dev'
LIMIT = 'limit'
LOGS = 'logs'
LIST = 'list'
PATH = 'path'
RAW = 'raw'
ROOT = 'root'

def mm(name): return '--' + name
def m(name): return '-' + name

VARIABLE = compile(r'(.*(?:[^$]|^))\${(\w+)\}(.*)')
MEMORY  = ':memory:'


class NamespaceWithVariables(Mapping):

    def __init__(self, ns):
        self._dict = vars(ns)

    def __getitem__(self, name):
        name = sub('-', '_', name)
        value = self._dict[name]
        try:
            match = VARIABLE.match(value)
            while match:
                value = match.group(1) + self[match.group(2)] + match.group(3)
                match = VARIABLE.match(value)
            return sub(r'\$\$', '$', value)
        except TypeError:
            return value

    def path(self, name, index=None, rooted=True):
        # special case sqlite3 in-memory database
        if self[name] == MEMORY: return self[name]
        path = self[name]
        if index is not None: path = path[index]
        path = expanduser(path)
        if rooted and relpath(path) and name != ROOT:
            path = join(self.path(ROOT), path)
        return realpath(normpath(path))

    def file(self, name, index=None, rooted=True):
        file = self.path(name, index=index, rooted=rooted)
        # special case sqlite3 in-memory database
        if file == MEMORY: return file
        path = dirname(file)
        if not exists(path):
            makedirs(path)
        return file

    def dir(self, name, index=None, rooted=True):
        path = self.path(name, index=index, rooted=rooted)
        if not exists(path):
            makedirs(path)
        return path

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self.__dict__)


def parser():

    parser = ArgumentParser(prog=PROGNAME)

    parser.add_argument(mm(DATABASE), action='store', default='${root}/database.sqla', metavar='FILE',
                        help='the database file')
    parser.add_argument(mm(DEV), action='store_true', help='enable development mode')
    parser.add_argument(mm(LOGS), action='store', default='logs', metavar='DIR',
                        help='the directory for logs')
    parser.add_argument(mm(ROOT), action='store', default='~/.ch2', metavar='DIR',
                        help='the root directory for the default configuration')
    parser.add_argument(m(V), mm(VERBOSITY), action='store', nargs=1, default=None, type=int, metavar='VERBOSITY',
                        help='output level for stderr (0: silent; 5:noisy)')
    parser.add_argument(mm(VERSION), action='version', version='0.0.4',
                        help='display version and exit')

    subparsers = parser.add_subparsers()

    diary = subparsers.add_parser(DIARY,
                                  help='daily diary - see `%s %s -h` for more details' % (PROGNAME, DIARY))
    diary.set_defaults(command=DIARY)

    dump = subparsers.add_parser(DUMP_FIT,
                                 help='display contents of fit file - ' +
                                      'see `%s %s -h` for more details' % (PROGNAME, DUMP_FIT))
    dump.add_argument(PATH, action='store', metavar='FIT-FILE', nargs=1,
                      help='the path to the fit file')
    dump.add_argument(mm(RAW), action='store_true', help='show low-level binary details?')
    dump.add_argument(mm(ALL_FIELDS), action='store_true', help='display undocumented fields?')
    dump.add_argument(mm(ALL_MESSAGES), action='store_true', help='display undocumented messages?')
    dump.add_argument(mm(AFTER), action='store', nargs=1, type=int, metavar='N', default=[0],
                      help='skip initial messages')
    dump.add_argument(mm(LIMIT), action='store', nargs=1, type=int, metavar='N', default=[-1],
                      help='limit number of messages displayed')
    dump.set_defaults(command=DUMP_FIT)

    help = subparsers.add_parser(HELP,
                                 help='display help - ' + 'see `%s %s -h` for more details' % (PROGNAME, HELP))
    help.add_argument(TOPIC, action='store', nargs='?', metavar=TOPIC,
                      help='the subject for help')
    help.set_defaults(command=HELP)

    injuries = subparsers.add_parser(INJURIES,
                                     help='manage injury entries - see `%s %s -h` for more details' %
                                          (PROGNAME, INJURIES))
    injuries.set_defaults(command=INJURIES)

    package = subparsers.add_parser(PACKAGE_FIT_PROFILE,
                                    help='parse and save the global fit profile (dev only) - ' +
                                         'see `%s %s -h` for more details' % (PROGNAME, PACKAGE_FIT_PROFILE))
    package.add_argument(PATH, action='store', metavar='PROFILE', nargs=1,
                         help='the path to the profile (Profile.xlsx)')
    package.set_defaults(command=PACKAGE_FIT_PROFILE)

    plan = subparsers.add_parser(PLAN,
                                 help='training plans - see `%s %s -h` for more details' % (PROGNAME, PLAN))
    plan.add_argument(mm(LIST), action='store_true',
                      help='list available plans')
    plan.add_argument(PLAN, action='store', metavar='PARAM', nargs='*',
                      help='the plan name and possible parameters')
    plan.set_defaults(command=PLAN)

    schedules = subparsers.add_parser(SCHEDULES,
                                      help='manage schedules - see `%s %s -h` for more details' % (PROGNAME, SCHEDULES))
    schedules.set_defaults(command=SCHEDULES)

    return parser

