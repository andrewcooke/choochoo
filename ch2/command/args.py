
from argparse import ArgumentParser
from genericpath import exists
from os import makedirs
from os.path import dirname, expanduser, realpath, normpath, relpath, join
from re import compile, sub
from typing import Mapping

from ..lib.date import to_date

PROGNAME = 'ch2'
COMMAND = 'command'
SUB_COMMAND = 'sub_command'
TOPIC = 'topic'

ACTIVITIES = 'activities'
CONSTANTS = 'constants'
DATA = 'data'
DEFAULT_CONFIG = 'default-config'
DIARY = 'diary'
FIT = 'fit'
GARMIN = 'garmin'
H, HELP = 'h', 'help'
NO_OP = 'no-op'
PACKAGE_FIT_PROFILE = 'package-fit-profile'
STATISTICS = 'statistics'
TEST_SCHEDULE = 'test-schedule'

ACTIVITY = 'activity'
ACTIVITY_GROUPS = 'activity-groups'
ACTIVITY_JOURNALS = 'activity-journals'
AFTER = 'after'
ALL_MESSAGES = 'all-messages'
ALL_FIELDS = 'all-fields'
CONSTRAINT = 'constraint'
CSV = 'csv'
DATABASE = 'database'
DATE = 'date'
DELETE = 'delete'
DESCRIBE = 'describe'
DEV = 'dev'
DIR = 'dir'
F = 'f'
FAST = 'fast'
FIELDS = 'fields'
FINISH = 'finish'
FORMAT = 'format'
FTHR = 'fthr'
FORCE, F = 'force', 'f'
GREP = 'grep'
GROUP = 'group'
LIKE = 'like'
LIMIT = 'limit'
LOGS = 'logs'
LIST = 'list'
M, MESSAGE = 'm', 'message'
MATCH = 'match'
MAX_COLUMNS = 'max-columns'
MAX_COLWIDTH = 'max-colwidth'
MAX_ROWS = 'max-rows'
MESSAGES = 'messages'
MONITOR = 'monitor'
MONITOR_JOURNALS = 'monitor-journals'
MONTH = 'month'
MONTHS = 'months'
NAME = 'name'
NAMES = 'names'
NO_DIARY = 'no-diary'
NOT = 'not'
OWNER = 'owner'
PASS = 'pass'
PATH = 'path'
PLAN = 'plan'
PRINT = 'print'
PWD = 'pwd'
RECORDS = 'records'
ROOT = 'root'
SEGMENT_JOURNALS = 'segment-journals'
SEGMENTS = 'segments'
SERVICE = 'service'
SET = 'set'
SCHEDULE = 'schedule'
SOURCE_IDS = 'source-ids'
START = 'start'
STATISTIC_NAMES = 'statistic-names'
STATISTIC_JOURNALS = 'statistic-journals'
STATISTIC_QUARTILES = 'statistic-quartiles'
TABLES = 'tables'
UNLOCK = 'unlock'
USER = 'user'
V, VERBOSITY = 'v', 'verbosity'
VALUE = 'value'
VERSION = 'version'
W, WARN = 'w', 'warn'
WIDTH = 'width'
YEAR = 'year'


def mm(name): return '--' + name
def m(name): return '-' + name


VARIABLE = compile(r'(.*(?:[^$]|^))\${(\w+)\}(.*)')
MEMORY = ':memory:'


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

    parser.add_argument(m(F), mm(DATABASE), action='store', default='${root}/database.sqln', metavar='FILE',
                        help='the database file')
    parser.add_argument(mm(DEV), action='store_true', help='enable development mode')
    parser.add_argument(mm(LOGS), action='store', default='logs', metavar='DIR',
                        help='the directory for logs')
    parser.add_argument(mm(ROOT), action='store', default='~/.ch2', metavar='DIR',
                        help='the root directory for the default configuration')
    parser.add_argument(m(V), mm(VERBOSITY), action='store', nargs=1, default=None, type=int, metavar='VERBOSITY',
                        help='output level for stderr (0: silent; 5:noisy)')
    parser.add_argument(m(V.upper()), mm(VERSION), action='version', version='0.7.4',
                        help='display version and exit')

    subparsers = parser.add_subparsers()

    activities = subparsers.add_parser(ACTIVITIES, help='read activity data')
    activities.add_argument(mm(FORCE), action='store_true', help='re-read file and delete existing data')
    activities.add_argument(mm(FAST), action='store_true', help='do not calculate statistics')
    activities.add_argument(PATH, action='store', metavar='PATH', nargs='+',
                            help='path to fit file(s)')
    activities.set_defaults(command=ACTIVITIES)

    constant = subparsers.add_parser(CONSTANTS, help='set and examine constants')
    constant_flags = constant.add_mutually_exclusive_group()
    constant_flags.add_argument(mm(DELETE), action='store_true', help='delete existing value(s)')
    constant_flags.add_argument(mm(SET), action='store_true', help='store a new value')
    constant.add_argument(mm(FORCE), action='store_true', help='confirm deletion(s) without value')
    constant.add_argument(NAME, action='store', nargs='?', metavar='NAME', help='constant name')
    constant.add_argument(DATE, action='store', nargs='?', metavar='DATE', help='date when measured')
    constant.add_argument(VALUE, action='store', nargs='?', metavar='VALUE', help='constant value')
    constant.set_defaults(command=CONSTANTS)

    data = subparsers.add_parser(DATA)
    data_format = data.add_mutually_exclusive_group()
    data_format.add_argument(mm(PRINT), action='store_const', dest=FORMAT, const=PRINT, help='default format')
    data_format.add_argument(mm(CSV), action='store_const', dest=FORMAT, const=CSV, help='CVS format')
    data_format.add_argument(mm(DESCRIBE), action='store_const', dest=FORMAT, const=DESCRIBE, help='summary format')
    data.add_argument(mm(MAX_COLUMNS), action='store', metavar='N', type=int, help='pandas max_columns attribute')
    data.add_argument(mm(MAX_COLWIDTH), action='store', metavar='N', type=int, help='pandas max_colwidth attribute')
    data.add_argument(mm(MAX_ROWS), action='store', metavar='N', type=int, help='pandas max_rows attribute')
    data.add_argument(mm(WIDTH), action='store', metavar='N', type=int, help='pandas width attribute')
    data_sub = data.add_subparsers()
    data_activity_groups = data_sub.add_parser(ACTIVITY_GROUPS)
    data_activity_groups.set_defaults(sub_command=ACTIVITY_GROUPS)
    data_activity_journals = data_sub.add_parser(ACTIVITY_JOURNALS)
    data_activity_journals.add_argument(GROUP, action='store', metavar='GROUP', help='activity group name')
    data_activity_journals.add_argument(mm(START), action='store', nargs='?', metavar='TIME', help='start time')
    data_activity_journals.add_argument(mm(FINISH), action='store', nargs='?', metavar='TIME', help='finish time')
    data_activity_journals.set_defaults(sub_command=ACTIVITY_JOURNALS)
    data_segment_journals = data_sub.add_parser(SEGMENT_JOURNALS)
    data_segment_journals.set_defaults(sub_command=SEGMENT_JOURNALS)
    data_segments = data_sub.add_parser(SEGMENTS)
    data_segments.set_defaults(sub_command=SEGMENTS)
    data_statistic_names = data_sub.add_parser(STATISTIC_NAMES)
    data_statistic_names.add_argument(NAMES, action='store', nargs='*', metavar='NAME', help='statistic names')
    data_statistic_names.set_defaults(sub_command=STATISTIC_NAMES)
    data_statistic_journals = data_sub.add_parser(STATISTIC_JOURNALS)
    data_statistic_journals.add_argument(NAMES, action='store', nargs='*', metavar='NAME', help='statistic names')
    data_statistic_journals.add_argument(mm(START), action='store', nargs='?', metavar='TIME', help='start time')
    data_statistic_journals.add_argument(mm(FINISH), action='store', nargs='?', metavar='TIME', help='finish time')
    data_statistic_journals.add_argument(mm(OWNER), action='store', nargs='?', metavar='OWNER',
                                         help='typically the class that created the data')
    data_statistic_journals.add_argument(mm(CONSTRAINT), action='store', nargs='?', metavar='CONSTRAINT',
                                         help='a value that makes the name unique (eg activity group)')
    data_statistic_journals.add_argument(mm(SCHEDULE), action='store', nargs='?', metavar='SCHEDULE',
                                         help='the schedule on which some statistics are calculated')
    data_statistic_journals.add_argument(mm(SOURCE_IDS), action='store', nargs='*', metavar='ID',
                                         help='the source IDs for the statistic')
    data_statistic_journals.set_defaults(sub_command=STATISTIC_JOURNALS)
    data_statistic_quartiles = data_sub.add_parser(STATISTIC_QUARTILES)
    data_statistic_quartiles.add_argument(NAMES, action='store', nargs='*', metavar='NAME', help='statistic names')
    data_statistic_quartiles.add_argument(mm(START), action='store', nargs='?', metavar='TIME', help='start time')
    data_statistic_quartiles.add_argument(mm(FINISH), action='store', nargs='?', metavar='TIME', help='finish time')
    data_statistic_quartiles.add_argument(mm(OWNER), action='store', nargs='?', metavar='OWNER',
                                          help='typically the class that created the data')
    data_statistic_quartiles.add_argument(mm(CONSTRAINT), action='store', nargs='?', metavar='CONSTRAINT',
                                          help='a value that makes the name unique (eg activity group)')
    data_statistic_quartiles.add_argument(mm(SCHEDULE), action='store', nargs='?', metavar='SCHEDULE',
                                          help='the schedule on which some statistics are calculated')
    data_statistic_quartiles.add_argument(mm(SOURCE_IDS), action='store', nargs='*', metavar='ID',
                                          help='the source IDs for the statistic')
    data_statistic_quartiles.set_defaults(sub_command=STATISTIC_QUARTILES)
    data_monitor_journals = data_sub.add_parser(MONITOR_JOURNALS)
    data_monitor_journals.set_defaults(sub_command=MONITOR_JOURNALS)
    data.set_defaults(command=DATA, format=PRINT)

    default_config = subparsers.add_parser(DEFAULT_CONFIG,
                                           help='configure the default database ' +
                                                '(see docs for full configuration instructions)')
    default_config.add_argument(mm(NO_DIARY), action='store_true', help='skip diary creation (for migration)')
    default_config.set_defaults(command=DEFAULT_CONFIG)

    diary = subparsers.add_parser(DIARY, help='daily diary and summary')
    diary.add_argument(DATE, action='store', metavar='DATE', nargs='?', type=to_date,
                       help='an optional date to display (default is today)')
    diary_summary = diary.add_mutually_exclusive_group()
    diary_summary.add_argument(mm(MONTH), action='store_const', dest=SCHEDULE, const='m',
                               help='show monthly summary')
    diary_summary.add_argument(mm(YEAR), action='store_const', dest=SCHEDULE, const='y',
                               help='show yearly summary')
    diary_summary.add_argument(mm(SCHEDULE), metavar='SCHEDULE',
                               help='show summary for given schedule')
    diary.set_defaults(command=DIARY)

    fit = subparsers.add_parser(FIT, help='display contents of fit file')
    fit.add_argument(PATH, action='store', metavar='PATH', nargs='+',
                     help='path to fit file')
    fit_format = fit.add_mutually_exclusive_group(required=True)
    fit_format.add_argument(mm(RECORDS), action='store_const', dest=FORMAT, const=RECORDS,
                            help='show high-level structure (ordered by time)')
    fit_format.add_argument(mm(TABLES), action='store_const', dest=FORMAT, const=TABLES,
                            help='show high-level structure (grouped in tables)')
    fit_format.add_argument(mm(GREP), action='store', dest=GREP, nargs='+', metavar='MSG:FLD[=VAL]',
                            help='show med-level matching entries')
    fit_format.add_argument(mm(CSV), action='store_const', dest=FORMAT, const=CSV,
                            help='show med-level structure in CSV format')
    fit_format.add_argument(mm(MESSAGES), action='store_const', dest=FORMAT, const=MESSAGES,
                            help='show low-level message structure')
    fit_format.add_argument(mm(FIELDS), action='store_const', dest=FORMAT, const=FIELDS,
                            help='show low-level field structure (more details)')
    fit.add_argument(mm(AFTER), action='store', type=int, metavar='N', default=0,
                     help='skip initial messages')
    fit.add_argument(mm(LIMIT), action='store', type=int, metavar='N', default=-1,
                     help='limit number of messages')
    fit.add_argument(mm(ALL_FIELDS), action='store_true',
                     help='display undocumented high-level fields')
    fit.add_argument(mm(ALL_MESSAGES), action='store_true',
                     help='display undocumented high-level messages')
    fit.add_argument(m(M), mm(MESSAGE), action='store', nargs='+', metavar='MSG',
                     help='display only named high-level messages')
    fit.add_argument(m(W), mm(WARN), action='store_true',
                     help='additional warning messages')
    fit.add_argument(mm(NAME), action='store_true',
                     help='display file name')
    fit.add_argument(mm(NOT), action='store_true',
                     help='display file names that don\'t match (with --grep --name)')
    fit.add_argument(mm(MATCH), action='store', type=int, default=1,
                     help='number of matches to display (with --grep, default 1, -1 for all)')
    fit.set_defaults(command=FIT, format=GREP)   # because that's the only one not set if the option is used

    garmin = subparsers.add_parser(GARMIN, help='download monitor data from garmin connect')
    garmin.add_argument(DIR, action='store', metavar='DIR',
                        help='the directory where FIT files are stored')
    garmin.add_argument(mm(USER), action='store', metavar='USER', required=True,
                        help='garmin connect username')
    garmin.add_argument(mm(PASS), action='store', metavar='PASSWORD', required=True,
                        help='garmin connect password')
    garmin.add_argument(mm(DATE), action='store', metavar='DATE', type=to_date,
                        help='date to download')
    garmin.set_defaults(command=GARMIN)

    help = subparsers.add_parser(HELP, help='display help')
    help.add_argument(TOPIC, action='store', nargs='?', metavar=TOPIC,
                      help='the subject for help')
    help.set_defaults(command=HELP)

    monitor = subparsers.add_parser(MONITOR, help='read monitor data')
    monitor.add_argument(mm(FORCE), action='store_true', help='re-read file and delete existing data')
    monitor.add_argument(mm(FAST), action='store_true', help='do not calculate statistics')
    monitor.add_argument(PATH, action='store', metavar='PATH', nargs='+',
                         help='path to fit file(s)')
    monitor.set_defaults(command=MONITOR)

    statistics = subparsers.add_parser(STATISTICS, help='(re-)generate statistics')
    statistics.add_argument(mm(FORCE), action='store_true', help='delete existing statistics')
    statistics.add_argument(AFTER, action='store', nargs='?', metavar='DATE',
                            help='date from which statistics are deleted')
    statistics.add_argument(mm(LIKE), action='store', metavar='PATTERN',
                            help='run only matching pipeline classes')
    statistics.set_defaults(command=STATISTICS)

    noop = subparsers.add_parser(NO_OP,
                                 help='used within jupyter (no-op from cmd line)')
    noop.set_defaults(command=NO_OP)

    package_fit_profile = subparsers.add_parser(PACKAGE_FIT_PROFILE,
                                                help='parse and save the global fit profile (dev only)')
    package_fit_profile.add_argument(PATH, action='store', metavar='PROFILE',
                                     help='the path to the profile (Profile.xlsx)')
    package_fit_profile.add_argument(m(W), mm(WARN), action='store_true',
                                     help='additional warning messages')
    package_fit_profile.set_defaults(command=PACKAGE_FIT_PROFILE)

    test_schedule = subparsers.add_parser(TEST_SCHEDULE, help='print schedule locations in a calendar')
    test_schedule.add_argument(SCHEDULE, action='store', metavar='SCHEDULE',
                               help='the schedule to test')
    test_schedule.add_argument(mm(START), action='store', metavar='DATE',
                               help='the date to start displaying data')
    test_schedule.add_argument(mm(MONTHS), action='store', metavar='N', type=int,
                               help='the number of months to display')
    test_schedule.set_defaults(command=TEST_SCHEDULE)

    unlock = subparsers.add_parser(UNLOCK,
                                   help='remove database locking (emergency only!)')
    unlock.add_argument(mm(FORCE), action='store_true', help='confirm unlock')
    unlock.set_defaults(command=UNLOCK)

    return parser


def bootstrap_file(file, *args, configurator=None, post_config=None):

    from ..lib.log import make_log
    from ..config.database import config
    from ..squeal.database import Database

    args = [mm(DATABASE), file.name] + list(args)
    if configurator:
        log, db = config(*args)
        configurator(log, db)
    args += post_config if post_config else []
    args = NamespaceWithVariables(parser().parse_args(args))
    log = make_log(args)
    db = Database(args, log)

    return args, log, db
