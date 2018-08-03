
from argparse import ArgumentParser
from genericpath import exists
from os import makedirs
from os.path import dirname, expanduser, realpath, normpath, relpath, join
from re import compile, sub
from typing import Mapping


PROGNAME = 'ch2'
COMMAND = 'command'

DIARY = 'diary'
INJURIES = 'injuries'
SCHEDULES = 'schedules'
PLAN = 'plan'
PACKAGE_FIT_PROFILE = 'package-fit-profile'
DUMP_FIT = 'dump-fit'

ROOT = 'root'
DATABASE = 'database'
LOGS = 'logs'
LIST = 'list'
PATH = 'path'

def mm(name): return '--' + name


VARIABLE = compile(r'(.*(?:[^$]|^))\${(\w+)\}(.*)')
MEMORY  = ':memory:'


class NamespaceWithVariables(Mapping):

    def __init__(self, ns):
        self._dict = vars(ns)

    def __getitem__(self, name):
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

    parser = ArgumentParser()

    parser.add_argument(mm(ROOT), action='store', default='~/.ch2', metavar='DIR',
                        help='The root directory for the default configuration')
    parser.add_argument(mm(LOGS), action='store', default='logs', metavar='DIR',
                        help='The directory for logs')
    parser.add_argument(mm(DATABASE), action='store', default='${root}/database.sqla', metavar='FILE',
                        help='The database file')

    subparsers = parser.add_subparsers()

    diary = subparsers.add_parser(DIARY,
                                  help='daily diary - see `%s %s -h` for more details' % (PROGNAME, DIARY))
    diary.set_defaults(command=DIARY)

    injuries = subparsers.add_parser(INJURIES,
                                     help='manage injury entries - see `%s %s -h` for more details' %
                                          (PROGNAME, INJURIES))
    injuries.set_defaults(command=INJURIES)

    schedules = subparsers.add_parser(SCHEDULES,
                                      help='manage schedules - see `%s %s -h` for more details' % (PROGNAME, SCHEDULES))
    schedules.set_defaults(command=SCHEDULES)

    plan = subparsers.add_parser(PLAN,
                                 help='training plans - see `%s %s -h` for more details' % (PROGNAME, PLAN))
    plan.add_argument(mm(LIST), action='store_true',
                      help='List available plans')
    plan.add_argument(PLAN, action='store', metavar='PARAM', nargs='*',
                      help='The plan name and possible parameters')
    plan.set_defaults(command=PLAN)

    package = subparsers.add_parser(PACKAGE_FIT_PROFILE,
                                    help='parse and save the global fit profile (dev only) - ' +
                                         'see `%s %s -h` for more details' % (PROGNAME, PACKAGE_FIT_PROFILE))
    package.add_argument(PATH, action='store', metavar='PROFILE', nargs=1,
                         help='The path to the profile (Profile.xlsx)')
    package.set_defaults(command=PACKAGE_FIT_PROFILE)

    dump = subparsers.add_parser(DUMP_FIT,
                                 help='print contents of fit file to screen - ' +
                                      'see `%s %s -h` for more details' % (PROGNAME, DUMP_FIT))
    dump.add_argument(PATH, action='store', metavar='FIT', nargs=1,
                      help='The path to the fit file')
    dump.set_defaults(command=DUMP_FIT)

    return parser
