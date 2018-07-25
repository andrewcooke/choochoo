
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

ROOT = 'root'
DATABASE = 'database'
LOGS = 'logs'
LIST = 'list'


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

    def path(self, name):
        # special case sqlite3 in-memory database
        if self[name] == MEMORY: return self[name]
        path = expanduser(self[name])
        if relpath(path) and name != ROOT:
            path = join(self.path(ROOT), path)
        return realpath(normpath(path))

    def file(self, name):
        file = self.path(name)
        # special case sqlite3 in-memory database
        if file == MEMORY: return file
        path = dirname(file)
        if not exists(path):
            makedirs(path)
        return file

    def dir(self, name):
        path = self.path(name)
        if not exists(path):
            makedirs(path)
        return path

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self.__dict__)


def parser():

    p = ArgumentParser()

    p.add_argument(mm(ROOT), action='store', default='~/.ch2', metavar='DIR',
                   help='The root directory for the default configuration')
    p.add_argument(mm(LOGS), action='store', default='logs', metavar='DIR',
                   help='The directory for logs')
    p.add_argument(mm(DATABASE), action='store', default='${root}/database.sqla', metavar='FILE',
                   help='The database file')

    subparsers = p.add_subparsers()

    p_diary = subparsers.add_parser(DIARY,
                                    help='daily diary - see `%s %s -h` for more details' % (PROGNAME, DIARY))
    p_diary.set_defaults(command=DIARY)

    p_injuries = subparsers.add_parser(INJURIES,
                                       help='manage injury entries - see `%s %s -h` for more details' %
                                            (PROGNAME, INJURIES))
    p_injuries.set_defaults(command=INJURIES)

    p_schedules = subparsers.add_parser(SCHEDULES,
                                        help='manage schedules - see `%s %s -h` for more details' % (PROGNAME, SCHEDULES))
    p_schedules.set_defaults(command=SCHEDULES)

    p_plan = subparsers.add_parser(PLAN,
                                   help='training plans - see `%s %s -h` for more details' % (PROGNAME, PLAN))
    p_plan.add_argument(mm(LIST), action='store_true',
                        help='List available plans')
    p_plan.add_argument(PLAN, action='store', metavar='PARAM', nargs='*',
                        help='The plan name and possible parameters')
    p_plan.set_defaults(command=PLAN)

    return p
