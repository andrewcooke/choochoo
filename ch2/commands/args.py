
from argparse import ArgumentParser
from genericpath import exists
from logging import getLogger
from os import makedirs
from os.path import dirname, expanduser, realpath, normpath, relpath, join
from re import compile, sub
from typing import Mapping

from ..lib.date import to_date, to_time

log = getLogger(__name__)

CH2_VERSION = '0.17.2'

PROGNAME = 'ch2'
COMMAND = 'command'
SUB_COMMAND = 'sub_command'
TOPIC = 'topic'

ACTIVITIES = 'activities'
CONSTANTS = 'constants'
DEFAULT_CONFIG = 'default-config'
DIARY = 'diary'
DUMP = 'dump'
FIT = 'fit'
FIX_FIT = 'fix-fit'
GARMIN = 'garmin'
H, HELP = 'h', 'help'
NO_OP = 'no-op'
PACKAGE_FIT_PROFILE = 'package-fit-profile'
STATISTICS = 'statistics'
TEST_SCHEDULE = 'test-schedule'

ACTIVITY = 'activity'
ACTIVITY_GROUP = 'activity-group'
ACTIVITY_GROUPS = 'activity-groups'
ACTIVITY_JOURNALS = 'activity-journals'
ACTIVITY_JOURNAL_ID = 'activity-journal-id'
ADD_HEADER = 'add-header'
AFTER = 'after'
AFTER_BYTES = 'after-bytes'
AFTER_RECORDS = 'after-records'
ALL_MESSAGES = 'all-messages'
ALL_FIELDS = 'all-fields'
BORDER = 'border'
COMPACT = 'compact'
CONSTRAINT = 'constraint'
CONSTANT = 'constant'
CONTEXT = 'context'
CSV = 'csv'
D = 'd'
DATABASE = 'database'
DATE = 'date'
DELETE = 'delete'
DESCRIBE = 'describe'
DEV = 'dev'
DIR = 'dir'
DISCARD = 'discard'
DROP = 'drop'
F = 'f'
FAST = 'fast'
FIELD = 'field'
FIELDS = 'fields'
FINISH = 'finish'
FIX_CHECKSUM = 'fix-checksum'
FIX_HEADER = 'fix-header'
FORMAT = 'format'
FORCE = 'force'
FTHR = 'fthr'
GREP = 'grep'
GROUP = 'group'
HEADER_SIZE = 'header-size'
HEIGHT = 'height'
INTERNAL = 'internal'
JUPYTER = 'jupyter'
K = 'k'
KARG = 'karg'
LABEL = 'label'
LATITUDE = 'latitude'
LIKE = 'like'
LIMIT_BYTES = 'limit-bytes'
LIMIT_RECORDS = 'limit-records'
L, LOG = 'l', 'log'
LOGS = 'logs'
LONGITUDE = 'longitude'
LIST = 'list'
M, MESSAGE = 'm', 'message'
MATCH = 'match'
MAX_BACK_CNT = 'max-back-cnt'
MAX_COLUMNS = 'max-columns'
MAX_COLWIDTH = 'max-colwidth'
MAX_DROP_CNT = 'max-drop-cnt'
MAX_DELTA_T = 'max-delta-t'
MAX_FWD_LEN = 'max-fwd-len'
MAX_ROWS = 'max-rows'
MAX_RECORD_LEN = 'max-record-len'
MIN_SYNC_CNT = 'min-sync-cnt'
MONITOR = 'monitor'
MONITOR_JOURNALS = 'monitor-journals'
MONTH = 'month'
MONTHS = 'months'
NAME = 'name'
NAME_BAD = 'name-bad'
NAME_GOOD = 'name-good'
NAMES = 'names'
NO_DIARY = 'no-diary'
NO_VALIDATE = 'no-validate'
NOT = 'not'
O, OUTPUT = 'o', 'output'
OWNER = 'owner'
PASS = 'pass'
PATH = 'path'
PLAN = 'plan'
PRINT = 'print'
PROFILE_VERSION = 'profile-version'
PROTOCOL_VERSION = 'protocol-version'
PWD = 'pwd'
RAW = 'raw'
RECORDS = 'records'
ROOT = 'root'
SEGMENT_JOURNALS = 'segment-journals'
SEGMENTS = 'segments'
SERVICE = 'service'
SET = 'set'
SCHEDULE = 'schedule'
SLICES = 'slices'
SOURCE_IDS = 'source-ids'
START = 'start'
STATISTIC_NAMES = 'statistic-names'
STATISTIC_JOURNALS = 'statistic-journals'
STATISTIC_QUARTILES = 'statistic-quartiles'
TABLE = 'table'
TABLES = 'tables'
TOKENS = 'tokens'
UNLOCK = 'unlock'
USER = 'user'
VALIDATE = 'validate'
V, VERBOSITY = 'v', 'verbosity'
VALUE = 'value'
VERSION = 'version'
W, WARN = 'w', 'warn'
WAYPOINTS = 'waypoints'
WIDTH = 'width'
WORKER = 'worker'
YEAR = 'year'


def mm(name): return '--' + name
def m(name): return '-' + name
def no(name): return mm('no-%s' % name)


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

    parser.add_argument(m(F), mm(DATABASE), action='store', default='${root}/database.sqlq', metavar='FILE',
                        help='the database file')
    parser.add_argument(no(JUPYTER), action='store_false', dest=JUPYTER,
                        help='don\'t start the Jupyter server')
    parser.add_argument(mm(DEV), action='store_true', help='show stack trace on error')
    parser.add_argument(mm(LOGS), action='store', default='logs', metavar='DIR',
                        help='the directory for logs')
    parser.add_argument(m(L), mm(LOG), action='store', metavar='FILE',
                        help='the file for the log (command name by default)')
    parser.add_argument(mm(ROOT), action='store', default='~/.ch2', metavar='DIR',
                        help='the root directory for the default configuration')
    parser.add_argument(m(V), mm(VERBOSITY), action='store', nargs=1, default=None, type=int, metavar='VERBOSITY',
                        help='output level for stderr (0: silent; 5:noisy)')
    parser.add_argument(m(V.upper()), mm(VERSION), action='version', version=CH2_VERSION,
                        help='display version and exit')

    subparsers = parser.add_subparsers()

    activities = subparsers.add_parser(ACTIVITIES, help='read activity data')
    activities.add_argument(mm(FORCE), action='store_true', help='re-read file and delete existing data')
    activities.add_argument(mm(FAST), action='store_true', help='do not calculate statistics')
    activities.add_argument(PATH, action='store', metavar='PATH', nargs='+',
                            help='path to fit file(s)')
    activities.add_argument(m(D.upper()), mm(CONSTANT), action='store', nargs='*', metavar='NAME=VALUE', dest=CONSTANT,
                            help='constant(s) to be stored with the activities')
    activities.add_argument(m(K.upper()), mm(KARG), action='store', nargs='*', metavar='NAME=VALUE', dest=KARG,
                            help='keyword argument(s) to be passed to the pipelines')
    activities.add_argument(mm(WORKER), action='store', metavar='ID', type=int,
                            help='internal use only (identifies sub-process workers)')
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

    dump = subparsers.add_parser(DUMP)  # todo - this one needs tests!
    dump_format = dump.add_mutually_exclusive_group()
    dump_format.add_argument(mm(PRINT), action='store_const', dest=FORMAT, const=PRINT, help='default format')
    dump_format.add_argument(mm(CSV), action='store_const', dest=FORMAT, const=CSV, help='CVS format')
    dump_format.add_argument(mm(DESCRIBE), action='store_const', dest=FORMAT, const=DESCRIBE, help='summary format')
    dump.add_argument(mm(MAX_COLUMNS), action='store', metavar='N', type=int, help='pandas max_columns attribute')
    dump.add_argument(mm(MAX_COLWIDTH), action='store', metavar='N', type=int, help='pandas max_colwidth attribute')
    dump.add_argument(mm(MAX_ROWS), action='store', metavar='N', type=int, help='pandas max_rows attribute')
    dump.add_argument(mm(WIDTH), action='store', metavar='N', type=int, help='pandas width attribute')
    dump_sub = dump.add_subparsers()
    dump_statistics = dump_sub.add_parser(STATISTICS)
    dump_statistics.add_argument(NAMES, action='store', nargs='*', metavar='NAME', help='statistic names')
    dump_statistics.add_argument(mm(START), action='store', metavar='TIME', help='start time')
    dump_statistics.add_argument(mm(FINISH), action='store', metavar='TIME', help='finish time')
    dump_statistics.add_argument(mm(OWNER), action='store', metavar='OWNER',
                                 help='typically the class that created the data')
    dump_statistics.add_argument(mm(CONSTRAINT), action='store', metavar='CONSTRAINT',
                                 help='a value that makes the name unique (eg activity group)')
    dump_statistics.add_argument(mm(SCHEDULE), action='store', metavar='SCHEDULE',
                                 help='the schedule on which some statistics are calculated')
    dump_statistics.add_argument(mm(SOURCE_IDS), action='store', nargs='*', metavar='ID', type=int,
                                 help='the source IDs for the statistic')
    dump_statistics.set_defaults(sub_command=STATISTICS)
    sump_statistic_quartiles = dump_sub.add_parser(STATISTIC_QUARTILES)
    sump_statistic_quartiles.add_argument(NAMES, action='store', nargs='*', metavar='NAME', help='statistic names')
    sump_statistic_quartiles.add_argument(mm(START), action='store', metavar='TIME', help='start time')
    sump_statistic_quartiles.add_argument(mm(FINISH), action='store', metavar='TIME', help='finish time')
    sump_statistic_quartiles.add_argument(mm(OWNER), action='store', metavar='OWNER',
                                          help='typically the class that created the data')
    sump_statistic_quartiles.add_argument(mm(CONSTRAINT), action='store', metavar='CONSTRAINT',
                                          help='a value that makes the name unique (eg activity group)')
    sump_statistic_quartiles.add_argument(mm(SCHEDULE), action='store', metavar='SCHEDULE',
                                          help='the schedule on which some statistics are calculated')
    sump_statistic_quartiles.add_argument(mm(SOURCE_IDS), action='store', nargs='*', metavar='ID', type=int,
                                          help='the source IDs for the statistic')
    sump_statistic_quartiles.set_defaults(sub_command=STATISTIC_QUARTILES)
    sump_table = dump_sub.add_parser(TABLE)
    sump_table.add_argument(NAME, action='store', metavar='NAME', help='table name')
    sump_table.set_defaults(sub_command=TABLE)
    dump.set_defaults(command=DUMP, format=PRINT)

    default_config = subparsers.add_parser(DEFAULT_CONFIG,
                                           help='configure the default database ' +
                                                '(see docs for full configuration instructions)')
    default_config.add_argument(mm(NO_DIARY), action='store_true', help='skip diary creation (for migration)')
    default_config.set_defaults(command=DEFAULT_CONFIG)

    diary = subparsers.add_parser(DIARY, help='daily diary and summary')
    diary.add_argument(DATE, action='store', metavar='DATE', nargs='?',
                       help='an optional date to display (default is today)')
    diary.add_argument(mm(FAST), action='store_true',
                       help='skip update of statistics on exit')
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
    fit_format = fit.add_argument_group(title='output format (one required)').add_mutually_exclusive_group(required=True)
    fit_format.add_argument(mm(GREP), action='store', dest=GREP, nargs='+', metavar='MSG:FLD[=VAL]',
                            help='show matching entries')
    fit_format.add_argument(mm(RECORDS), action='store_const', dest=FORMAT, const=RECORDS,
                            help='show high-level structure (ordered by time)')
    fit_format.add_argument(mm(TABLES), action='store_const', dest=FORMAT, const=TABLES,
                            help='show high-level structure (grouped in tables)')
    fit_format.add_argument(mm(CSV), action='store_const', dest=FORMAT, const=CSV,
                            help='show high-level structure (in CSV format)')
    fit_format.add_argument(mm(TOKENS), action='store_const', dest=FORMAT, const=TOKENS,
                            help='show low-level tokens')
    fit_format.add_argument(mm(FIELDS), action='store_const', dest=FORMAT, const=FIELDS,
                            help='show low-level fields (within tokens)')
    fit.add_argument(mm(AFTER_RECORDS), action='store', type=int, metavar='N', default=None,
                     help='skip initial records')
    fit.add_argument(mm(LIMIT_RECORDS), action='store', type=int, metavar='N', default=-1,
                     help='limit number of records displayed')
    fit.add_argument(mm(AFTER_BYTES), action='store', type=int, metavar='N', default=None,
                     help='skip initial bytes')
    fit.add_argument(mm(LIMIT_BYTES), action='store', type=int, metavar='N', default=-1,
                     help='limit number of bytes displayed')
    fit.add_argument(mm(INTERNAL), action='store_true',
                     help='display internal messages')
    fit.add_argument(mm(ALL_MESSAGES), action='store_true',
                     help='display undocumented messages')
    fit.add_argument(mm(ALL_FIELDS), action='store_true',
                     help='display undocumented fields')
    fit.add_argument(m(M), mm(MESSAGE), action='store', nargs='+', metavar='MSG',
                     help='display named messages (--grep, --records, --tables)')
    fit.add_argument(m(F), mm(FIELD), action='store', nargs='+', metavar='FLD',
                     help='display named fields (--grep, --records, --tables')
    fit.add_argument(m(W), mm(WARN), action='store_true',
                     help='log additional warnings')
    fit.add_argument(mm(WIDTH), action='store', type=int,
                     help='display width for some formats')
    fit.add_argument(mm(NO_VALIDATE), action='store_true',
                     help='do not validate checksum, length')
    fit.add_argument(mm(MAX_DELTA_T), action='store', type=float, metavar='S',
                     help='max seconds between timestamps (and non-decreasing)')
    fit.add_argument(mm(NAME), action='store_true',
                     help='print file name')
    fit.add_argument(mm(NOT), action='store_true',
                     help='print file names that don\'t match (--grep --name)')
    fit.add_argument(mm(MATCH), action='store', type=int, default=-1,
                     help='max number of matches (--grep, default -1 for all)')
    fit.add_argument(mm(COMPACT), action='store_true',
                     help='no space between records (--grep)')
    fit.add_argument(mm(CONTEXT), action='store_true',
                     help='display entire record (--grep)')
    fit.set_defaults(command=FIT, format=GREP)   # because that's the only one not set if the option is used

    fix_fit = subparsers.add_parser(FIX_FIT, help='fix a corrupted fit file')
    fix_fit.add_argument(PATH, action='store', metavar='PATH', nargs='+',
                         help='path to fit file')
    fix_fit.add_argument(m(W), mm(WARN), action='store_true',
                         help='additional warning messages')
    fix_fit_output = fix_fit.add_argument_group(title='output (default hex to stdout)').add_mutually_exclusive_group()
    fix_fit_output.add_argument(m(O), mm(OUTPUT), action='store',
                                help='output file for fixed data (otherwise, stdout)')
    fix_fit_output.add_argument(mm(DISCARD), action='store_true',
                                help='discard output (otherwise, stdout)')
    fix_fit_output.add_argument(mm(RAW), action='store_true',
                                help='raw binary to stdout (otherwise, hex encoded)')
    fix_fit_output.add_argument(mm(NAME_BAD), action='store_false', dest=NAME, default=None,
                                help='print file name if bad')
    fix_fit_output.add_argument(mm(NAME_GOOD), action='store_true', dest=NAME, default=None,
                                help='print file name if good')
    fix_fit_process = fix_fit.add_argument_group(title='processing (default disabled)')
    fix_fit_process.add_argument(mm(ADD_HEADER), action='store_true',
                                 help='preprend a new header')
    fix_fit_stage = fix_fit_process.add_mutually_exclusive_group()
    fix_fit_stage.add_argument(mm(DROP), action='store_true',
                               help='search for data that can be dropped to give a successful parse')
    fix_fit_stage.add_argument(mm(SLICES), action='store', metavar='A:B,C:D,...',
                               help='data slices to pick')
    fix_fit_stage.add_argument(mm(START), action='store', type=to_time, metavar='TIME',
                               help='change start time')
    fix_fit_process.add_argument(mm(FIX_HEADER), action='store_true',
                                 help='modify the header')
    fix_fit_process.add_argument(mm(FIX_CHECKSUM), action='store_true',
                                 help='modify the checksum')
    fix_fit_process.add_argument(no(FORCE), action='store_false', dest=FORCE,
                                 help='don\'t parse record contents')
    fix_fit_process.add_argument(no(VALIDATE), action='store_false', dest=VALIDATE,
                                 help='don\'t validate the final data')
    fix_fit_params = fix_fit.add_argument_group(title='parameters')
    fix_fit_params.add_argument(mm(HEADER_SIZE), action='store', type=int, metavar='N',
                                help='header size (validation and/or new header)')
    fix_fit_params.add_argument(mm(PROTOCOL_VERSION), action='store', type=int, metavar='N',
                                help='protocol version (validation and/or new header)')
    fix_fit_params.add_argument(mm(PROFILE_VERSION), action='store', type=int, metavar='N',
                                help='profile version (validation and/or new header)')
    fix_fit_params.add_argument(mm(MIN_SYNC_CNT), action='store', type=int, metavar='N', default=3,
                                help='minimum number of records to read for synchronization')
    fix_fit_params.add_argument(mm(MAX_RECORD_LEN), action='store', type=int, metavar='N', default=None,
                                help='maximum record length')
    fix_fit_params.add_argument(mm(MAX_DROP_CNT), action='store', type=int, metavar='N', default=1,
                                help='maximum number of gaps to drop')
    fix_fit_params.add_argument(mm(MAX_BACK_CNT), action='store', type=int, metavar='N', default=3,
                                help='maximum number of readable records to discard in a single gap')
    fix_fit_params.add_argument(mm(MAX_FWD_LEN), action='store', type=int, metavar='N', default=200,
                                help='maximum number of bytes to drop in a single gap')
    fix_fit_params.add_argument(mm(MAX_DELTA_T), action='store', type=float, metavar='S',
                                help='max number of seconds between timestamps')
    fix_fit.set_defaults(command=FIX_FIT)

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
    monitor.add_argument(m(K.upper()), mm(KARG), action='store', nargs='*', metavar='NAME=VALUE', dest=KARG,
                         help='keyword argument(s) to be passed to the pipelines')
    monitor.add_argument(mm(WORKER), action='store', metavar='ID', type=int,
                         help='internal use only (identifies sub-process workers)')
    monitor.set_defaults(command=MONITOR)

    statistics = subparsers.add_parser(STATISTICS, help='(re-)generate statistics')
    statistics.add_argument(mm(FORCE), action='store_true',
                            help='delete existing statistics')
    statistics.add_argument(mm(LIKE), action='store', metavar='PATTERN',
                            help='run only matching pipeline classes')
    statistics.add_argument(START, action='store', metavar='START', nargs='?',
                            help='optional start date')
    statistics.add_argument(FINISH, action='store', metavar='FINISH', nargs='?',
                            help='optional finish date (if start also given)')
    statistics.add_argument(m(K.upper()), mm(KARG), action='store', nargs='*', metavar='NAME=VALUE', dest=KARG,
                            help='keyword argument(s) to be passed to the pipelines')
    statistics.add_argument(mm(WORKER), action='store', metavar='ID', type=int,
                            help='internal use only (identifies sub-process workers)')
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

    unlock = subparsers.add_parser(UNLOCK, help='remove database locking')
    unlock.set_defaults(command=UNLOCK)

    return parser


def bootstrap_file(file, *args, configurator=None, post_config=None):

    from ..lib.log import make_log
    from ..config.database import config
    from ..squeal.database import Database

    args = [mm(DATABASE), file.name] + list(args)
    if configurator:
        db = config(*args)
        configurator(db)
    args += post_config if post_config else []
    args = NamespaceWithVariables(parser().parse_args(args))
    make_log(args)
    db = Database(args, log)

    return args, db


def parse_pairs(pairs):
    # simple name, value pairs.  owner and constraint supplied by command.
    d = {}
    if pairs is not None:
        for pair in pairs:
            name, value = pair.split('=', 1)
            for type in (int, float, to_time, bool):
                try:
                    value = type(value)
                    break
                except ValueError:
                    pass
            d[name] = value
    return d
