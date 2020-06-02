
from argparse import ArgumentParser
from genericpath import exists
from logging import getLogger
from os import makedirs
from os.path import join
from re import sub
from typing import Mapping

log = getLogger(__name__)

# this can be modified during development.  it will be reset from setup.py on release.
CH2_VERSION = '0.34.0'
# new database on minor releases.  not sure this will always be a good idea.  we will see.
DB_VERSION = '-'.join(CH2_VERSION.split('.')[:2])
DB_EXTN = '.db'   # used to use .sql but auto-complete for sqlite3 didn't work

PERMANENT = 'permanent'

PROGNAME = 'ch2'
COMMAND = 'command'

CALCULATE = 'calculate'
CONSTANTS = 'constants'
DATABASE = 'database'
DIARY = 'diary'
DUMP = 'dump'
FIT = 'fit'
FIX_FIT = 'fix-fit'
GARMIN = 'garmin'
H, HELP = 'h', 'help'
IMPORT = 'import'
JUPYTER = 'jupyter'
KIT = 'kit'
LOAD = 'load'
NO_OP = 'no-op'
PACKAGE_FIT_PROFILE = 'package-fit-profile'
READ = 'read'
SEARCH = 'search'
SHOW_SCHEDULE = 'show-schedule'
TEXT = 'text'
THUMBNAIL = 'thumbnail'
UNLOCK = 'unlock'
VALIDATE = 'validate'
WEB = 'web'

A = 'a'
ACTIVITY = 'activity'
ACTIVITY_GROUP = 'activity-group'
ACTIVITY_GROUPS = 'activity-groups'
ACTIVITY_JOURNALS = 'activity-journals'
ACTIVITY_JOURNAL_ID = 'activity-journal-id'
ACTIVITIES = 'activities'
ADD = 'add'
ADD_HEADER = 'add-header'
ADVANCED = 'advanced'
AFTER = 'after'
AFTER_BYTES = 'after-bytes'
AFTER_RECORDS = 'after-records'
ALL = 'all'
ALL_MESSAGES = 'all-messages'
ALL_FIELDS = 'all-fields'
ARG = 'arg'
BASE = 'base'
BIND = 'bind'
BORDER = 'border'
CHANGE = 'change'
CHECK = 'check'
CMD = 'cmd'
COLOR = 'color'
COMPACT = 'compact'
COMPONENT = 'component'
CONSTRAINT = 'constraint'
CONTEXT = 'context'
CSV = 'csv'
D = 'd'
DARK = 'dark'
DATA = 'data'
DATE = 'date'
DEFAULT = 'default'
DEFINE = 'define'
DELETE = 'delete'
DESCRIBE = 'describe'
DESCRIPTION = 'description'
DEV = 'dev'
DIR = 'dir'
DISABLE = 'disable'
DISCARD = 'discard'
DROP = 'drop'
EMPTY = 'empty'
ENABLE = 'enable'
F = 'f'
FAST = 'fast'
FIELD = 'field'
FIELDS = 'fields'
FILENAME_KIT = 'filename-kit'
FIX = 'fix'
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
ITEM = 'item'
K = 'k'
KARG = 'karg'
LABEL = 'label'
LATITUDE = 'latitude'
LIGHT = 'light'
LIKE = 'like'
LIMIT_BYTES = 'limit-bytes'
LIMIT_RECORDS = 'limit-records'
LOG = 'log'
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
MODEL = 'model'
MONITOR = 'monitor'
MONTH = 'month'
MONTHS = 'months'
NAME = 'name'
NAME_BAD = 'name-bad'
NAME_GOOD = 'name-good'
NAMES = 'names'
NEW = 'new'
NOT = 'not'
NOTEBOOKS = 'notebooks'
O, OUTPUT = 'o', 'output'
OFF = 'off'
OWNER = 'owner'
PASS = 'pass'
PATH = 'path'
P, PATTERN = 'p', 'pattern'
PLAN = 'plan'
PORT = 'port'
PRINT = 'print'
PROFILE = 'profile'
PROFILE_VERSION = 'profile-version'
PROTOCOL_VERSION = 'protocol-version'
PWD = 'pwd'
QUERY = 'query'
RAW = 'raw'
READ_ONLY = 'read-only'
REBUILD = 'rebuild'
RECORDS = 'records'
REMOVE = 'remove'
RETIRE = 'retire'
ROOT = 'root'
RUN = 'run'
SEGMENT_JOURNALS = 'segment-journals'
SEGMENTS = 'segments'
SERVICE = 'service'
SET = 'set'
SCHEDULE = 'schedule'
SHOW = 'show'
SINGLE = 'single'
SLICES = 'slices'
SOURCE = 'source'
SOURCES = 'sources'
SOURCE_ID = 'source-id'
START = 'start'
STATISTICS = 'statistics'
STATISTIC_NAMES = 'statistic-names'
STATISTIC_JOURNALS = 'statistic-journals'
STATUS = 'status'
STOP = 'stop'
SUB_COMMAND = 'sub-command'
SYSTEM = 'system'
TABLE = 'table'
TABLES = 'tables'
TOKENS = 'tokens'
TOPIC = 'topic'
UNDO = 'undo'
UNLIKE = 'unlike'
UNSAFE = 'unsafe'
UNSET = 'unset'
USER = 'user'
V, VERBOSITY = 'v', 'verbosity'
VALUE = 'value'
VERSION = 'version'
W, WARN = 'w', 'warn'
WAYPOINTS = 'waypoints'
WIDTH = 'width'
WORKER = 'worker'
YEAR = 'year'
Y = 'y'


def mm(name): return '--' + name
def m(name): return '-' + name
def no(name): return 'no-%s' % name


class NamespaceWithVariables(Mapping):

    def __init__(self, ns):
        self._dict = vars(ns)

    def __getitem__(self, name):
        try:
            value = self._dict[name]
        except KeyError:
            value = self._dict[sub('-', '_', name)]
        return value

    def system_path(self, subdir=None, file=None, version=DB_VERSION, create=True):
        return base_system_path(self[BASE], subdir=subdir, file=file, version=version, create=create)

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self.__dict__)


def base_system_path(base, subdir=None, file=None, version=DB_VERSION, create=True):

    from ..lib.utils import clean_path

    dir = base
    if version: dir = join(dir, version)
    if subdir: dir = join(dir, subdir)
    dir = clean_path(dir)
    if create and not exists(dir): makedirs(dir)
    if file:
        return join(dir, file)
    else:
        return dir


def color(color):
    if color.lower() not in (LIGHT, DARK, OFF):
        raise Exception(f'Bad color: {color} ({LIGHT}|{DARK}|{OFF})')
    return color


def make_parser(with_noop=False):

    from ..lib import to_date, to_time

    parser = ArgumentParser(prog=PROGNAME)

    parser.add_argument(mm(BASE), default=f'~/.ch2', metavar='DIR',
                        help='the base directory for data (default ~/.ch2)')
    parser.add_argument(mm(READ_ONLY), action='store_true',
                        help='read-only database (so errors on write)')
    parser.add_argument(mm(LOG), metavar='FILE',
                        help='the file name for the log (command name by default)')
    parser.add_argument(mm(COLOR), type=color,
                        help=f'pretty stdout log - {LIGHT}|{DARK}|{OFF} (CAPS to save)')
    parser.add_argument(m(V), mm(VERBOSITY), default=4, type=int, metavar='N',
                        help='output level for stderr (0: silent; 5:noisy)')
    parser.add_argument(mm(DEV), action='store_true',
                        help='verbose log and stack trace on error')
    parser.add_argument(m(V.upper()), mm(VERSION), action='version', version=CH2_VERSION,
                        help='display version and exit')

    subparsers = parser.add_subparsers(title='commands', dest=COMMAND)

    # high-level commands used daily

    help = subparsers.add_parser(HELP, help='display help')
    help.add_argument(TOPIC, nargs='?', metavar=TOPIC,
                      help='the subject for help')

    web = subparsers.add_parser(WEB, help='the web interface (probably all you need)')
    web_cmds = web.add_subparsers(title='sub-commands', dest=SUB_COMMAND, required=True)

    def add_web_server_args(cmd):
        cmd.add_argument(mm(BIND), default='localhost', help='bind address (default localhost)')
        cmd.add_argument(mm(PORT), default=8000, type=int, help='port to use')

    add_web_server_args(web_cmds.add_parser(START, help='start the web server'))
    web_cmds.add_parser(STOP, help='stop the web server')
    web_cmds.add_parser(STATUS, help='display status of web server')
    add_web_server_args(web_cmds.add_parser(SERVICE, help='internal use only - use start/stop'))

    read = subparsers.add_parser(READ, help='read data (also calls calculate)')
    read.add_argument(mm(FORCE), action='store_true', help='reprocess existing data')
    read.add_argument(mm(KIT), m(K), action='append', default=[], metavar='ITEM',
                      help='kit items associated with activities')
    read.add_argument(PATH, metavar='PATH', nargs='*', default=[], help='path to fit file(s) for activities')
    read.add_argument(m(K.upper()), mm(KARG), action='append', default=[], metavar='NAME=VALUE',
                      help='keyword argument to be passed to the pipelines (can be repeated)')
    read.add_argument(mm(WORKER), metavar='ID', type=int, help='internal use only (identifies sub-process workers)')
    read.add_argument(mm(DISABLE), action='store_true', help='disable following options (they enable by default)')
    read.add_argument(mm(ACTIVITIES), action='store_true', help='enable (or disable) processing of activity data')
    read.add_argument(mm(MONITOR), action='store_true', help='enable (or disable) processing of monitor data')
    read.add_argument(mm(CALCULATE), action='store_true', help='enable (or disable) calculating statistics')

    def add_search_query(cmd):
        cmd.add_argument(QUERY, metavar='QUERY', default=[], nargs='+',
                         help='search terms (similar to SQL)')
        cmd.add_argument(mm(SHOW), metavar='NAME', default=[], nargs='+',
                         help='show value from matching entries')
        cmd.add_argument(mm(SET), metavar='NAME=VALUE', help='update matching entries')

    search = subparsers.add_parser(SEARCH, help='search the database')
    search_cmds = search.add_subparsers(title='search target', dest=SUB_COMMAND, required=True)
    search_text = search_cmds.add_parser(TEXT, help='search for text in activities')
    add_search_query(search_text)
    search_activities = search_cmds.add_parser(ACTIVITIES, help='search for activities')
    add_search_query(search_activities)
    search_sources = search_cmds.add_parser(SOURCES, help='search for sources')
    add_search_query(search_sources)

    # low-level commands used often

    constants = subparsers.add_parser(CONSTANTS, help='set and examine constants')
    constants_cmds = constants.add_subparsers(title='sub-commands', dest=SUB_COMMAND, required=True)
    constants_list = constants_cmds.add_parser(LIST, help='list all names')
    constants_show = constants_cmds.add_parser(SHOW, help='show a value (or all values)')
    constants_show.add_argument(NAME, nargs='?', metavar='NAME', help='name (omit for all)')
    constants_show.add_argument(DATE, nargs='?', metavar='DATE',
                               help='date of value to show (omit for all)')
    constants_add = constants_cmds.add_parser(ADD, help='add a new constant')
    constants_add.add_argument(NAME, metavar='NAME', help='name')
    constants_add.add_argument(mm(SINGLE), action='store_true', help='allow only a single (constant) value')
    constants_add.add_argument(mm(DESCRIPTION), help='optional description')
    constants_add.add_argument(mm(VALIDATE), help='optional validation class')
    constants_set = constants_cmds.add_parser(SET, help='set or modify a value')
    constants_set.add_argument(NAME, metavar='NAME', help='name')
    constants_set.add_argument(VALUE, metavar='VALUE', help='value')
    constants_set.add_argument(DATE, nargs='?', metavar='DATE',
                              help='date when measured (omit for all time)')
    constants_set.add_argument(mm(FORCE), action='store_true', help='allow over-writing existing values')
    constants_unset = constants_cmds.add_parser(UNSET, help='delete a value (or all values)')
    constants_unset.add_argument(NAME, metavar='NAME', help='name')
    constants_unset.add_argument(DATE, nargs='?', metavar='DATE',
                                 help='date of value to delete (omit for all)')
    constants_unset.add_argument(mm(FORCE), action='store_true', help='allow deletion of all values')
    constants_remove = constants_cmds.add_parser(REMOVE, help='remove a constant (after deleting all values)')
    constants_remove.add_argument(NAME, metavar='NAME', help='name')
    constants_remove.add_argument(mm(FORCE), action='store_true', help='allow remove of multiple constants')

    validate = subparsers.add_parser(VALIDATE, help='check (and optionally fix) data in the database')
    validate.add_argument(mm(FIX), action='store_true', help='correct errors when possible')

    jupyter = subparsers.add_parser(JUPYTER, help='access jupyter')
    jupyter_cmds = jupyter.add_subparsers(title='sub-commands', dest=SUB_COMMAND, required=True)
    jupyter_cmds.add_parser(LIST, help='list available templates')
    jupyter_show = jupyter_cmds.add_parser(SHOW, help='display a template (starting server if needed)')
    jupyter_show.add_argument(NAME, help='the template name')
    jupyter_show.add_argument(ARG, nargs='*', help='template arguments')
    jupyter_cmds.add_parser(START, help='start a background service')
    jupyter_cmds.add_parser(STOP, help='stop the background service')
    jupyter_cmds.add_parser(STATUS, help='display status of background service')
    jupyter_cmds.add_parser(SERVICE, help='internal use only - use start/stop')

    kit = subparsers.add_parser(KIT, help='manage kit')
    kit_cmds = kit.add_subparsers(title='sub-commands', dest=SUB_COMMAND, required=True)
    kit_start = kit_cmds.add_parser(START, help='define a new item (new bike, new shoe)')
    kit_start.add_argument(GROUP, help='item group (bike, shoe, etc)')
    kit_start.add_argument(ITEM, help='item name (cotic, adidas, etc)')
    kit_start.add_argument(DATE, nargs='?', help='when created (default now)')
    kit_start.add_argument(mm(FORCE), action='store_true', help='confirm creation of a new group')
    kit_finish = kit_cmds.add_parser(FINISH, help='retire an item')
    kit_finish.add_argument(ITEM, help='item name')
    kit_finish.add_argument(DATE, nargs='?', help='when to retire (default now)')
    kit_finish.add_argument(mm(FORCE), action='store_true', help='confirm change of existing date')
    kit_delete = kit_cmds.add_parser(DELETE, help='remove all entries for an item or group')
    kit_delete.add_argument(NAME, help='item or group to delete')
    kit_delete.add_argument(mm(FORCE), action='store_true', help='confirm group deletion')
    kit_change = kit_cmds.add_parser(CHANGE, help='replace (or add) a part (wheel, innersole, etc)')
    kit_change.add_argument(ITEM, help='item name (cotic, adidas, etc)')
    kit_change.add_argument(COMPONENT, help='component type (chain, laces, etc)')
    kit_change.add_argument(MODEL, help='model description')
    kit_change.add_argument(DATE, nargs='?', help='when changed (default now)')
    kit_change.add_argument(mm(FORCE), action='store_true', help='confirm creation of a new component')
    kit_change.add_argument(mm(START), action='store_true', help='set default date to start of item')
    kit_undo = kit_cmds.add_parser(UNDO, help='remove a change')
    kit_undo.add_argument(ITEM, help='item name')
    kit_undo.add_argument(COMPONENT, help='component type')
    kit_undo.add_argument(MODEL, help='model description')
    kit_undo.add_argument(DATE, nargs='?', help='active date (to disambiguate models; default now)')
    kit_undo.add_argument(mm(ALL), action='store_true', help='remove all models (rather than single date)')
    kit_show = kit_cmds.add_parser(SHOW, help='display kit data')
    kit_show.add_argument(NAME, nargs='?', help='group or item to display (default all)')
    kit_show.add_argument(DATE, nargs='?', help='when to display (default now)')
    kit_show.add_argument(mm(CSV), action='store_true', help='CSV format')
    kit_statistics = kit_cmds.add_parser(STATISTICS, help='display statistics')
    kit_statistics.add_argument(NAME, nargs='?', help='group, item, component or model')
    kit_statistics.add_argument(mm(CSV), action='store_true', help='CSV format')
    kit_rebuild = kit_cmds.add_parser(REBUILD, help='rebuild database entries')
    kit_dump = kit_cmds.add_parser(DUMP, help='dump to script')
    kit_dump.add_argument(mm(CMD), help='command to use instead of ch2')

    # low-level commands use rarely

    database = subparsers.add_parser(DATABASE, help='configure the database')
    database_cmds = database.add_subparsers(title='sub-commands', dest=SUB_COMMAND, required=True)
    database_check = database_cmds.add_parser(CHECK, help="check config")
    database_check.add_argument(mm(no(DATA)), action='store_true', help='check database has no data loaded')
    database_check.add_argument(mm(no(DATABASE)), action='store_true', help='check database has no configuration')
    database_check.add_argument(mm(no(ACTIVITY_GROUPS)), action='store_true',
                                help='check database has no activity groups defined')
    database_list = database_cmds.add_parser(LIST, help='list available profiles')
    database_load = database_cmds.add_parser(LOAD, help="configure using the given profile")
    database_profiles = database_load.add_subparsers(title='profile', dest=PROFILE, required=True)
    from ..config.utils import profiles
    for name in profiles():
        database_profile = database_profiles.add_parser(name)
        database_profile.add_argument(mm(no(DIARY)), action='store_true', help='skip diary creation (for migration)')
    database_delete = database_cmds.add_parser(DELETE, help='delete current data')
    database_delete.add_argument(mm(FORCE), action='store_true', help='are you sure?')

    import_ = subparsers.add_parser(IMPORT, help='import data from a previous version')
    import_.add_argument(SOURCE, help='version or path to import')
    import_.add_argument(mm(DISABLE), action='store_true', help='disable following options (they enable by default)')
    import_.add_argument(mm(DIARY), action='store_true', help='enable (or disable) import of diary data')
    import_.add_argument(mm(ACTIVITIES), action='store_true', help='enable (or disable) import of activity data')
    import_.add_argument(mm(KIT), action='store_true', help='enable (or disable) import of kit data')
    import_.add_argument(mm(CONSTANTS), action='store_true', help='enable (or disable) import of constant data')
    import_.add_argument(mm(SEGMENTS), action='store_true', help='enable (or disable) import of segment data')

    garmin = subparsers.add_parser(GARMIN, help='download monitor data from garmin connect')
    garmin.add_argument(DIR, metavar='DIR', nargs='?', help='the directory where FIT files are stored')
    garmin.add_argument(mm(USER), metavar='USER', help='garmin connect username')
    garmin.add_argument(mm(PASS), metavar='PASSWORD', help='garmin connect password')
    garmin.add_argument(mm(DATE), metavar='DATE', type=to_date, help='date to download')
    garmin.add_argument(mm(FORCE), action='store_true', help='allow longer date range')

    calculate = subparsers.add_parser(CALCULATE, help='(re-)calculate statistics')
    calculate.add_argument(mm(FORCE), action='store_true', help='delete existing statistics')
    calculate.add_argument(mm(LIKE), action='append', default=[], metavar='PATTERN',
                           help='run only matching pipeline classes')
    calculate.add_argument(mm(UNLIKE), action='append', default=[], metavar='PATTERN',
                           help='exclude matching pipeline classes')
    calculate.add_argument(START, metavar='START', nargs='?', help='optional start date')
    calculate.add_argument(FINISH, metavar='FINISH', nargs='?', help='optional finish date (if start also given)')
    calculate.add_argument(m(K.upper()), mm(KARG), action='append', default=[], metavar='NAME=VALUE',
                           help='keyword argument to be passed to the pipelines (can be repeated)')
    calculate.add_argument(mm(WORKER), metavar='ID', type=int,
                           help='internal use only (identifies sub-process workers)')

    fit = subparsers.add_parser(FIT, help='display contents of fit file')
    fit_cmds = fit.add_subparsers(title='sub-commands', dest=SUB_COMMAND, required=True)
    fit_grep = fit_cmds.add_parser(GREP, help='show matching entries')
    fit_records = fit_cmds.add_parser(RECORDS, help='show high-level structure (ordered by time)')
    fit_tables = fit_cmds.add_parser(TABLES, help='show high-level structure (grouped in tables)')
    fit_csv = fit_cmds.add_parser(CSV, help='show high-level structure (in CSV format)')
    fit_tokens = fit_cmds.add_parser(TOKENS, help='show low-level tokens')
    fit_fields = fit_cmds.add_parser(FIELDS, help='show low-level fields (within tokens)')

    def add_fit_general(cmd):
        cmd.add_argument(mm(AFTER_RECORDS), type=int, metavar='N', default=None,
                         help='skip initial records')
        cmd.add_argument(mm(LIMIT_RECORDS), type=int, metavar='N', default=-1,
                         help='limit number of records displayed')
        cmd.add_argument(mm(AFTER_BYTES), type=int, metavar='N', default=None,
                         help='skip initial bytes')
        cmd.add_argument(mm(LIMIT_BYTES), type=int, metavar='N', default=-1,
                         help='limit number of bytes displayed')
        cmd.add_argument(m(W), mm(WARN), action='store_true', help='log additional warnings')
        cmd.add_argument(mm(no(VALIDATE)), action='store_true', help='do not validate checksum, length')
        cmd.add_argument(mm(MAX_DELTA_T), type=float, metavar='S',
                         help='validate seconds between timestamps (and non-decreasing)')
        cmd.add_argument(mm(NAME), action='store_true', help='print file name')
        cmd.add_argument(PATH, metavar='PATH', nargs='+', help='path to fit file')

    def add_fit_grep(cmd):
        cmd.add_argument(mm(NOT), action='store_true', help='print file names that don\'t match (with --name)')
        cmd.add_argument(mm(MATCH), type=int, default=-1, help='max number of matches (default -1 for all)')
        cmd.add_argument(mm(COMPACT), action='store_true', help='no space between records')
        cmd.add_argument(mm(CONTEXT), action='store_true', help='display entire record')
        cmd.add_argument(m(P), mm(PATTERN), nargs='+', metavar='MSG:FLD[=VAL]', required=True,
                         help='pattern to match (separate from PATH with --)')

    def add_fit_high_level(cmd):
        cmd.add_argument(m(M), mm(MESSAGE), nargs='+', metavar='MSG', help='display named messages')
        cmd.add_argument(m(F), mm(FIELD), nargs='+', metavar='FLD', help='display named fields')
        cmd.add_argument(mm(INTERNAL), action='store_true', help='display internal messages')

    def add_fit_very_high_level(cmd):
        cmd.add_argument(mm(ALL_MESSAGES), action='store_true', help='display undocumented messages')
        cmd.add_argument(mm(ALL_FIELDS), action='store_true', help='display undocumented fields')

    for cmd in fit_grep, fit_records, fit_tables, fit_csv, fit_tokens, fit_fields:
        add_fit_general(cmd)

    for cmd in fit_records, fit_tables, fit_csv:
        add_fit_high_level(cmd)

    for cmd in fit_records, fit_tables:
        add_fit_very_high_level(cmd)

    add_fit_grep(fit_grep)

    for cmd in fit_grep, fit_records, fit_tables:
        cmd.add_argument(mm(WIDTH), type=int,
                         help='display width')

    fix_fit = subparsers.add_parser(FIX_FIT, help='fix a corrupted fit file')
    fix_fit.add_argument(PATH, metavar='PATH', nargs='+', help='path to fit file')
    fix_fit.add_argument(m(W), mm(WARN), action='store_true', help='additional warning messages')
    fix_fit_output = fix_fit.add_argument_group(title='output (default hex to stdout)').add_mutually_exclusive_group()
    fix_fit_output.add_argument(m(O), mm(OUTPUT), action='store',
                                help='output file for fixed data (otherwise, stdout)')
    fix_fit_output.add_argument(mm(DISCARD), action='store_true', help='discard output (otherwise, stdout)')
    fix_fit_output.add_argument(mm(RAW), action='store_true', help='raw binary to stdout (otherwise, hex encoded)')
    fix_fit_output.add_argument(mm(NAME_BAD), action='store_false', dest=NAME, default=None,
                                help='print file name if bad')
    fix_fit_output.add_argument(mm(NAME_GOOD), action='store_true', dest=NAME, default=None,
                                help='print file name if good')
    fix_fit_process = fix_fit.add_argument_group(title='processing (default disabled)')
    fix_fit_process.add_argument(mm(ADD_HEADER), action='store_true', help='preprend a new header')
    fix_fit_stage = fix_fit_process.add_mutually_exclusive_group()
    fix_fit_stage.add_argument(mm(DROP), action='store_true',
                               help='search for data that can be dropped to give a successful parse')
    fix_fit_stage.add_argument(mm(SLICES), metavar='A:B,C:D,...', help='data slices to pick')
    fix_fit_stage.add_argument(mm(START), type=to_time, metavar='TIME', help='change start time')
    fix_fit_process.add_argument(mm(FIX_HEADER), action='store_true', help='modify the header')
    fix_fit_process.add_argument(mm(FIX_CHECKSUM), action='store_true', help='modify the checksum')
    fix_fit_process.add_argument(mm(no(FORCE)), action='store_false', dest=FORCE,
                                 help='don\'t parse record contents')
    fix_fit_process.add_argument(mm(no(VALIDATE)), action='store_false', dest=VALIDATE,
                                 help='don\'t validate the final data')
    fix_fit_params = fix_fit.add_argument_group(title='parameters')
    fix_fit_params.add_argument(mm(HEADER_SIZE), type=int, metavar='N',
                                help='header size (validation and/or new header)')
    fix_fit_params.add_argument(mm(PROTOCOL_VERSION), type=int, metavar='N',
                                help='protocol version (validation and/or new header)')
    fix_fit_params.add_argument(mm(PROFILE_VERSION), type=int, metavar='N',
                                help='profile version (validation and/or new header)')
    fix_fit_params.add_argument(mm(MIN_SYNC_CNT), type=int, metavar='N', default=3,
                                help='minimum number of records to read for synchronization')
    fix_fit_params.add_argument(mm(MAX_RECORD_LEN), type=int, metavar='N', default=None,
                                help='maximum record length')
    fix_fit_params.add_argument(mm(MAX_DROP_CNT), type=int, metavar='N', default=1,
                                help='maximum number of gaps to drop')
    fix_fit_params.add_argument(mm(MAX_BACK_CNT), type=int, metavar='N', default=3,
                                help='maximum number of readable records to discard in a single gap')
    fix_fit_params.add_argument(mm(MAX_FWD_LEN), type=int, metavar='N', default=200,
                                help='maximum number of bytes to drop in a single gap')
    fix_fit_params.add_argument(mm(MAX_DELTA_T), type=float, metavar='S',
                                help='max number of seconds between timestamps')

    thumbnail = subparsers.add_parser(THUMBNAIL,
                                      help='generate a thumbnail map of an activity')
    thumbnail.add_argument(ACTIVITY, metavar='ACTIVITY',
                           help='an activity ID or date')

    if with_noop:
        noop = subparsers.add_parser(NO_OP,
                                     help='used within jupyter (no-op from cmd line)')

    package_fit_profile = subparsers.add_parser(PACKAGE_FIT_PROFILE,
                                                help='parse and save the global fit profile (dev only)')
    package_fit_profile.add_argument(PATH, metavar='PROFILE',
                                     help='the path to the profile (Profile.xlsx)')
    package_fit_profile.add_argument(m(W), mm(WARN), action='store_true',
                                     help='additional warning messages')

    show_schedule = subparsers.add_parser(SHOW_SCHEDULE, help='print schedule locations in a calendar')
    show_schedule.add_argument(SCHEDULE, metavar='SCHEDULE', help='schedule to test')
    show_schedule.add_argument(mm(START), metavar='DATE', help='date to start displaying data')
    show_schedule.add_argument(mm(MONTHS), metavar='N', type=int, help='number of months to display')

    unlock = subparsers.add_parser(UNLOCK, help='remove database locking')

    return parser


def bootstrap_dir(base, *args, configurator=None, post_config=None):
    # used in tests, given a base directory

    from ..lib.log import make_log_from_args
    from ..sql.database import connect, sqlite_uri
    from ..sql.system import System, SystemConstant

    args = [mm(BASE), base] + list(args)
    if configurator:
        ns, db = connect(args)
        sys = System(ns)
        with db.session_context() as s:
            configurator(sys, s, base)
    args += post_config if post_config else []
    ns = NamespaceWithVariables(make_parser().parse_args(args))
    make_log_from_args(ns)
    sys = System(ns)
    sys.set_constant(SystemConstant.DB_URI, sqlite_uri(join(base, ACTIVITY + DB_EXTN)))
    db = sys.get_database()

    return ns, sys, db


def parse_pairs(pairs, convert=True, multi=False, comma=False):

    from ..lib import to_time

    # simple name, value pairs. owner and constraint supplied by command.
    d = {}
    if pairs is not None:
        for pair in pairs:
            name, value = pair.split('=', 1)
            if convert:
                for type in (int, float, to_time):
                    try:
                        value = type(value)
                        break
                    except ValueError:
                        pass
            if multi:
                if name not in d:
                    d[name] = []
                d[name].append(value)
            elif comma:
                if name in d:
                    d[name] = d[name] + ',' + value
                else:
                    d[name] = value
            else:
                d[name] = value
    return d


def infer_flags(args, *names):
    flags = {name: args[name] for name in names}
    # if none were given, all are assumed
    if all(not flags[name] for name in names):
        for name in names: flags[name] = True
    if args[DISABLE]:
        for name in flags: flags[name] = not flags[name]
    return flags
