
from argparse import ArgumentParser
from genericpath import exists
from os import makedirs
from os.path import dirname, expanduser, realpath, normpath, relpath, join
from re import compile, sub
from typing import Mapping


PROGNAME = 'ch2'
COMMAND = 'command'
TOPIC = 'topic'

ACTIVITY = 'activity'
CONSTANT = 'constant'
DIARY = 'diary'
EXAMPLE_CONFIG = 'example-config'
FIT = 'fit'
H, HELP = 'h', 'help'
NO_OP = 'no-op'
PACKAGE_FIT_PROFILE = 'package-fit-profile'
STATISTICS = 'statistics'

AFTER = 'after'
ALL_MESSAGES = 'all-messages'
ALL_FIELDS = 'all-fields'
CSV = 'csv'
DATABASE = 'database'
DATE = 'date'
DELETE = 'delete'
DEV = 'dev'
DUMP_FORMAT = 'dump_format'
FIELDS = 'fields'
FINISH = 'finish'
FTHR = 'fthr'
FORCE, F = 'force', 'f'
LIMIT = 'limit'
LOGS = 'logs'
LIST = 'list'
MESSAGES = 'messages'
MONTH = 'month'
NAME = 'name'
PATH = 'path'
PLAN = 'plan'
RECORD, R = 'record', 'r'
RECORDS = 'records'
ROOT = 'root'
START = 'start'
TABLES = 'tables'
V, VERBOSITY = 'v', 'verbosity'
VALUE = 'value'
VERSION = 'version'
W, WARN = 'w', 'warn'
YEAR = 'year'


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

    parser.add_argument(mm(DATABASE), action='store', default='${root}/database.sqls', metavar='FILE',
                        help='the database file')
    parser.add_argument(mm(DEV), action='store_true', help='enable development mode')
    parser.add_argument(mm(LOGS), action='store', default='logs', metavar='DIR',
                        help='the directory for logs')
    parser.add_argument(mm(ROOT), action='store', default='~/.ch2', metavar='DIR',
                        help='the root directory for the default configuration')
    parser.add_argument(m(V), mm(VERBOSITY), action='store', nargs=1, default=None, type=int, metavar='VERBOSITY',
                        help='output level for stderr (0: silent; 5:noisy)')
    parser.add_argument(mm(VERSION), action='version', version='0.1.0',
                        help='display version and exit')

    subparsers = parser.add_subparsers()

    activity = subparsers.add_parser(ACTIVITY,
                                     help='add a new activity - see `%s %s -h` for more details' %
                                          (PROGNAME, ACTIVITY))
    activity_period = activity.add_mutually_exclusive_group()
    activity_period.add_argument(mm(MONTH), action='store_true', help='generate monthly summary')
    activity_period.add_argument(mm(YEAR), action='store_true', help='generate yearly summary')
    activity.add_argument(m(F), mm(FORCE), action='store_true', help='re-read file and delete existing data')
    activity.add_argument(ACTIVITY, action='store', metavar='ACTIVITY', nargs=1,
                          help='an activity name')
    activity.add_argument(PATH, action='store', metavar='PATH', nargs=1,
                          help='a fit file or directory containing fit files')
    activity.set_defaults(command=ACTIVITY)

    constant = subparsers.add_parser(CONSTANT,
                                     help='set and examine constants - see `%s %s -h` for more details' %
                                          (PROGNAME, CONSTANT))
    constant.add_argument(mm(DELETE), action='store_true', help='delete existing value(s)')
    constant.add_argument(mm(FORCE), action='store_true', help='confirm deletion(s) without value')
    constant.add_argument(NAME, action='store', nargs='?', metavar=NAME, help='constant name')
    constant.add_argument(DATE, action='store', nargs='?', metavar=DATE, help='date when measured')
    constant.add_argument(VALUE, action='store', nargs='?', metavar=VALUE, help='constant value')
    constant.set_defaults(command=CONSTANT)

    diary = subparsers.add_parser(DIARY,
                                  help='daily diary - see `%s %s -h` for more details' % (PROGNAME, DIARY))
    diary.add_argument(DATE, action='store', metavar='DATE', nargs='?',
                       help='an optional date to display (default is today)')
    diary.set_defaults(command=DIARY)

    fit = subparsers.add_parser(FIT,
                                help='display contents of fit file - ' +
                                     'see `%s %s -h` for more details' % (PROGNAME, FIT))
    fit.add_argument(PATH, action='store', metavar='FIT-FILE', nargs=1,
                     help='the path to the fit file')
    fit.add_argument(mm(AFTER), action='store', nargs=1, type=int, metavar='N', default=[0],
                     help='skip initial messages')
    fit.add_argument(mm(LIMIT), action='store', nargs=1, type=int, metavar='N', default=[-1],
                     help='limit number of messages displayed')
    fit_format = fit.add_mutually_exclusive_group()
    fit_format.add_argument(mm(RECORDS), action='store_const', dest=DUMP_FORMAT, const=RECORDS,
                            help='show high-level structure (ordered by time)')
    fit_format.add_argument(mm(TABLES), action='store_const', dest=DUMP_FORMAT, const=TABLES,
                            help='show high-level structure (default: grouped in tables)')
    fit_format.add_argument(mm(CSV), action='store_const', dest=DUMP_FORMAT, const=CSV,
                            help='show med-level structure (CSV format)')
    fit_format.add_argument(mm(MESSAGES), action='store_const', dest=DUMP_FORMAT, const=MESSAGES,
                            help='show low-level message structure')
    fit_format.add_argument(mm(FIELDS), action='store_const', dest=DUMP_FORMAT, const=FIELDS,
                            help='show low-level field structure (more details)')
    fit.add_argument(mm(ALL_FIELDS), action='store_true',
                     help='display undocumented fields (for %s, %s)' % (mm(RECORDS), mm(TABLES)))
    fit.add_argument(mm(ALL_MESSAGES), action='store_true',
                     help='display undocumented messages (for %s, %s)' % (mm(RECORDS), mm(TABLES)))
    fit.add_argument(m(R), mm(RECORD), action='store', metavar='name',
                     help='display only named record(s) (for %s, %s)' % (mm(RECORDS), mm(TABLES)))
    fit.add_argument(m(W), mm(WARN), action='store', metavar='name',
                     help='additional warning messages')
    fit.set_defaults(command=FIT, dump_format=TABLES)

    help = subparsers.add_parser(HELP,
                                 help='display help - ' + 'see `%s %s -h` for more details' % (PROGNAME, HELP))
    help.add_argument(TOPIC, action='store', nargs='?', metavar=TOPIC,
                      help='the subject for help')
    help.set_defaults(command=HELP)

    statistics = subparsers.add_parser(STATISTICS,
                                       help='(re-)generate statistics - ' +
                                            'see `%s %s -h` for more details' % (PROGNAME, STATISTICS))
    statistics.add_argument(mm(FORCE), action='store_true', help='delete existing statistics')
    statistics.add_argument(DATE, action='store', nargs='?', metavar=DATE,
                            help='date from which statistics are deleted')
    statistics.set_defaults(command=STATISTICS)

    example_config = subparsers.add_parser(EXAMPLE_CONFIG,
                                           help='configure the default database ' +
                                                '(see docs for full configuration instructions)')
    example_config.set_defaults(command=EXAMPLE_CONFIG)

    noop = subparsers.add_parser(NO_OP,
                                 help='used within jupyter (no-op from cmd line)')
    noop.set_defaults(command=NO_OP)

    package_fit_profile = subparsers.add_parser(PACKAGE_FIT_PROFILE,
                                                help='parse and save the global fit profile (dev only) - ' +
                                                     'see `%s %s -h` for more details' %
                                                     (PROGNAME, PACKAGE_FIT_PROFILE))
    package_fit_profile.add_argument(PATH, action='store', metavar='PROFILE', nargs=1,
                                     help='the path to the profile (Profile.xlsx)')
    package_fit_profile.add_argument(m(W), mm(WARN), action='store', metavar='name',
                                     help='additional warning messages')
    package_fit_profile.set_defaults(command=PACKAGE_FIT_PROFILE)

    return parser


def bootstrap_file(file, *args, configurator=None, post_config=None):

    from .log import make_log
    from ..config.database import config
    from ..squeal.database import Database

    args = [mm(DATABASE), file.name] + list(args)
    if configurator:
        log, db = config(*args)
        configurator(db)
    args += post_config if post_config else []
    args = NamespaceWithVariables(parser().parse_args(args))
    log = make_log(args)
    db = Database(args, log)

    return args, log, db
