
from argparse import ArgumentParser
from genericpath import exists
from logging import getLogger
from os import makedirs
from os.path import join

from ..common.args import mm, m, no, add_server_args, NamespaceWithVariables, color, add_data_source_args
from ..common.names import *
from ..common.names import UNDEF, COLOR, OFF, VERSION, USER
from ..lib.utils import parse_bool

log = getLogger(__name__)

# this can be modified during development.  it will be reset from setup.py on release.
CH2_VERSION = '0.36.0'
# new database on minor releases.  not sure this will always be a good idea.  we will see.
DB_VERSION = '-'.join(CH2_VERSION.split('.')[:2])

URI_DEFAULT = 'postgresql://{user}:{passwd}@{db-bind}:{db-port}/activity-{version}'
URI_PREVIOUS = 'postgresql://{user}:{passwd}@{db-bind}:{db-port}/activity-{version}?search_path={user}:previous'

PROGNAME = 'ch2'

WEB_PORT = 8000
JUPYTER_PORT = 8001

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
SEARCH = 'search'
SHOW_SCHEDULE = 'show-schedule'
SPARKLINE = 'sparkline'
TEXT = 'text'
THUMBNAIL = 'thumbnail'
UNLOCK = 'unlock'
VALIDATE = 'validate'

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
BACKUP = 'backup'
BATCH = 'batch'
BORDER = 'border'
CHANGE = 'change'
CHECK = 'check'
CMD = 'cmd'
COMPACT = 'compact'
COMPONENT = 'component'
CONSTRAINT = 'constraint'
CONTEXT = 'context'
CPROFILE = 'cprofile'
CSV = 'csv'
D = 'd'
DARK = 'dark'
DATA = 'data'
DATABASES = 'databases'
DATE = 'date'
DB = 'db'
DEFAULT = 'default'
DELETE = 'delete'
DESCRIBE = 'describe'
DESCRIPTION = 'description'
DEV = 'dev'
DIR = 'dir'
DISPLAY = 'display'
DISABLE = 'disable'
DISCARD = 'discard'
DROP = 'drop'
DURATION = 'duration'
EMPTY = 'empty'
ENABLE = 'enable'
ENGINE = 'engine'
F = 'f'
FAST = 'fast'
FIELD = 'field'
FIELDS = 'fields'
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
IMAGE_DIR = 'image-dir'
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
LOG_DIR = 'log-dir'
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
NOTEBOOK_DIR = 'notebook-dir'
O, OUTPUT = 'o', 'output'
OWNER = 'owner'
PATH = 'path'
PATTERN = 'pattern'
PERMANENT = 'permanent'
PLAN = 'plan'
PREVIOUS = 'previous'
PRINT = 'print'
PROCESS = 'process'
PROFILE = 'profile'
PROFILES = 'profiles'
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
SCHEMA = 'schema'
SCHEMAS = 'schemas'
SECURE = 'secure'
SECTOR = 'sector'
SHOW = 'show'
SINGLE = 'single'
SLICES = 'slices'
SOURCE = 'source'
SOURCES = 'sources'
SOURCE_ID = 'source-id'
START = 'start'
STATISTIC = 'statistic'
STATISTICS = 'statistics'
STATISTIC_NAMES = 'statistic-names'
STATISTIC_JOURNALS = 'statistic-journals'
STATUS = 'status'
STOP = 'stop'
SUB_COMMAND = 'sub-command'
SUB2_COMMAND = 'sub2-command'
SYSTEM = 'system'
TABLE = 'table'
TABLES = 'tables'
TOKENS = 'tokens'
TOPIC = 'topic'
UNDO = 'undo'
UNSAFE = 'unsafe'
UNSET = 'unset'
UPLOAD = 'upload'
USERS = 'users'
VALUE = 'value'
W, WARN = 'w', 'warn'
WAYPOINTS = 'waypoints'
WIDTH = 'width'
WORKER = 'worker'
YEAR = 'year'
Y = 'y'


def base_system_path(base, subdir=None, file=None, version=DB_VERSION, create=True):

    from ..common.io import clean_path

    dir = base
    if version: dir = join(dir, version)
    if subdir: dir = join(dir, subdir)
    dir = clean_path(dir)
    if create and not exists(dir): makedirs(dir)
    if file:
        return join(dir, file)
    else:
        return dir


def make_parser(with_noop=False):

    from ..lib import to_time
    from ..common.io import clean_path

    parser = ArgumentParser(prog=PROGNAME)

    parser.add_argument(mm(DEV), action='store_true',
                        help='verbose log and stack trace on error')
    parser.add_argument(mm(LOG), metavar='FILE',
                        help='the file name for the log (command name by default)')
    parser.add_argument(mm(LOG_DIR), metavar='DIR', default='{base}/{version}/logs',
                        help='the directory for the log')
    parser.add_argument(mm(COLOR), mm(COLOUR), type=color, dest=COLOR, default=DARK,
                        help=f'pretty stdout log - {LIGHT}|{DARK}|{OFF}')
    parser.add_argument(m(V), mm(VERBOSITY), default=UNDEF, type=int, metavar='N',
                        help='output level for stderr (0: silent; 5:noisy)')
    parser.add_argument(m(V.upper()), mm(VERSION), action='version', version=CH2_VERSION,
                        help='display version and exit')
    add_server_args(parser, DB, default_port=5432, name='database')
    add_data_source_args(parser, URI_DEFAULT)
    parser.add_argument(mm(BASE), default='~/.ch2', metavar='DIR', type=clean_path,
                        help='the base directory for data (default ~/.ch2)')
    parser.add_argument(mm(DATA), metavar='DIR', default='{base}/permanent',
                        help='the root directory for storing data on disk')
    parser.add_argument(mm(CPROFILE), metavar='DIR', nargs='?', action='append',
                        help='file for profiling data (development)')

    commands = parser.add_subparsers(title='commands', dest=COMMAND)

    help = commands.add_parser(HELP, help='display help',
                                 description='display additional help (beyond -h) for any command')
    help.add_argument(TOPIC, nargs='?', metavar=TOPIC, help='the subject for help')

    web = commands.add_parser(WEB, help='the web interface (probably all you need)',
                                description='start, stop and manage the web interface')
    web_cmds = web.add_subparsers(title='sub-commands', dest=SUB_COMMAND, required=True)

    def add_warning_args(cmd):
        prefix = WARN + '-'
        cmd.add_argument(mm(prefix + DATA), action='store_true', help='warn user that data may be lost')
        cmd.add_argument(mm(prefix + SECURE), action='store_true', help='warn user that the system is insecure')

    def add_image_dir(cmd):
        cmd.add_argument(mm(IMAGE_DIR), metavar='DIR', default='{base}/{version}/image',
                         help='image cache')

    def add_notebook_dir(cmd):
        cmd.add_argument(mm(NOTEBOOK_DIR), metavar='DIR', default='{base}/{version}/notebook',
                         help='notebook cache')

    def add_jupyter(cmd):
        cmd.add_argument(mm(JUPYTER), metavar='URL', default=f'http://localhost:{JUPYTER_PORT}/tree',
                         help='jupyter URL prefix')

    web_start = web_cmds.add_parser(START, help='start the web server', description='start the web server')
    add_server_args(web_start, prefix=WEB, default_port=WEB_PORT, name='web server')
    add_jupyter(web_start)
    add_warning_args(web_start)
    add_image_dir(web_start)
    add_notebook_dir(web_start)
    web_cmds.add_parser(STOP, help='stop the web server', description='stop the web server')
    web_cmds.add_parser(STATUS, help='display status of web server', description='display status of web server')
    web_service = web_cmds.add_parser(SERVICE, help='internal use only - use start/stop',
                                      description='internal use only - use start/stop')
    add_server_args(web_service, prefix=WEB, default_port=WEB_PORT, name='web server')
    add_jupyter(web_service)
    add_warning_args(web_service)
    add_image_dir(web_service)
    add_notebook_dir(web_service)

    upload = commands.add_parser(UPLOAD, help='upload data (copy FIT files to permanent store)',
                                 description='copy files to the permanent store and (optionally) process the data')
    upload.add_argument(mm(KARG), m(K.upper()), action='append', default=[], metavar='NAME=VALUE',
                        help='keyword argument to be passed to the pipelines (can be repeated)')
    upload.add_argument(mm(KIT), m(K), action='append', default=[], metavar='ITEM',
                        help='kit items associated with activities')
    upload.add_argument(mm(no(PROCESS)), action='store_false', dest=PROCESS,
                        help='do not call process after uploading')
    upload.add_argument(PATH, metavar='PATH', nargs='*', default=[], help='path to FIT file(s) containing data')

    process = commands.add_parser(PROCESS, help='process data (add information to the database)',
                                  description='read new files from the permanent store and calculate statistics')
    process.add_argument(mm(KARG), m(K.upper()), action='append', default=[], metavar='NAME=VALUE',
                         help='keyword argument to be passed to the pipelines (can be repeated)')
    # cannot be expressed in argparse (but checked in command) - like and worker are mutually exclusive
    process.add_argument(mm(LIKE), action='append', default=[], metavar='PATTERN',
                         help='run only matching pipeline classes')
    process.add_argument(mm(WORKER), metavar='ID', type=int,
                         help='internal use only (identifies sub-process workers)')
    process.add_argument(ARG, nargs='*', metavar='WORKER_ARG',
                         help=f'internal use only (tasks for {mm(WORKER)})')

    def add_search_query(cmd, query_help='search terms (similar to SQL)'):
        cmd.add_argument(QUERY, metavar='QUERY', default=[], nargs='+', help=query_help)
        cmd.add_argument(mm(SHOW), metavar='NAME', default=[], nargs='+',
                         help='show value from matching entries')
        cmd.add_argument(mm(SET), metavar='NAME=VALUE', help='update matching entries')

    search = commands.add_parser(SEARCH, help='search the database', description='search the database')
    search_cmds = search.add_subparsers(title='search target', dest=SUB_COMMAND, required=True)
    search_text = search_cmds.add_parser(TEXT, help='search for text in activities',
                                         description='search for text in activities')
    add_search_query(search_text, query_help='words to search for')
    search_activities = search_cmds.add_parser(ACTIVITIES, help='search for activities',
                                               description='search for activities')
    add_search_query(search_activities)
    search_sources = search_cmds.add_parser(SOURCES, help='search for sources',
                                            description='search for sources')
    add_search_query(search_sources)

    constants = commands.add_parser(CONSTANTS, help='set and examine constants',
                                      description='set and examine constants')
    constants_cmds = constants.add_subparsers(title='sub-commands', dest=SUB_COMMAND, required=True)
    constants_list = constants_cmds.add_parser(LIST, help='list all constant names',
                                               description='list all constant names')
    constants_show = constants_cmds.add_parser(SHOW, help='show a value (or all values)',
                                               description='show a constant\'s value (or all values)')
    constants_show.add_argument(NAME, nargs='?', metavar='NAME', help='name (omit for all)')
    constants_show.add_argument(DATE, nargs='?', metavar='DATE',
                               help='date of value to show (omit for all)')
    constants_add = constants_cmds.add_parser(ADD, help='add a new constant name',
                                              description='add a new constant name')
    constants_add.add_argument(NAME, metavar='NAME', help='name')
    constants_add.add_argument(mm(SINGLE), action='store_true', help='allow only a single (constant) value')
    constants_add.add_argument(mm(DESCRIPTION), help='optional description')
    constants_add.add_argument(mm(VALIDATE), help='optional validation class')
    constants_set = constants_cmds.add_parser(SET, help='set or modify a value',
                                              description='set or modify a constant\'s value')
    constants_set.add_argument(NAME, metavar='NAME', help='name')
    constants_set.add_argument(VALUE, metavar='VALUE', help='value')
    constants_set.add_argument(DATE, nargs='?', metavar='DATE',
                              help='date when measured (omit for all time)')
    constants_set.add_argument(mm(FORCE), action='store_true', help='allow over-writing existing values')
    constants_unset = constants_cmds.add_parser(UNSET, help='delete a value (or all values)',
                                                description='delete a value (or all values)')
    constants_unset.add_argument(NAME, metavar='NAME', help='name')
    constants_unset.add_argument(DATE, nargs='?', metavar='DATE',
                                 help='date of value to delete (omit for all)')
    constants_unset.add_argument(mm(FORCE), action='store_true', help='allow deletion of all values')
    constants_remove = constants_cmds.add_parser(REMOVE, help='remove a constant (after deleting all values)',
                                                 description='remove a constant\'s name (after deleting all values)')
    constants_remove.add_argument(NAME, metavar='NAME', help='name')
    constants_remove.add_argument(mm(FORCE), action='store_true', help='allow remove of multiple constants')

    validate = commands.add_parser(VALIDATE, help='check (and optionally fix) data in the database',
                                     description='check (and optionally fix) data in the database')
    validate.add_argument(mm(FIX), action='store_true', help='correct errors when possible')

    kit = commands.add_parser(KIT, help='manage kit',
                                description='add, remove, modify and display kit details')
    kit_cmds = kit.add_subparsers(title='sub-commands', dest=SUB_COMMAND, required=True)
    kit_start = kit_cmds.add_parser(START, help='define a new item (new bike, new shoe)',
                                    description='define a new item (new bike, new shoe)')
    kit_start.add_argument(GROUP, help='item group (bike, shoe, etc)')
    kit_start.add_argument(ITEM, help='item name (cotic, adidas, etc)')
    kit_start.add_argument(DATE, nargs='?', help='when created (default now)')
    kit_start.add_argument(mm(FORCE), action='store_true', help='confirm creation of a new group')
    kit_finish = kit_cmds.add_parser(FINISH, help='retire an item',
                                     description='retire an item (bike, shoe)')
    kit_finish.add_argument(ITEM, help='item name')
    kit_finish.add_argument(DATE, nargs='?', help='when to retire (default now)')
    kit_finish.add_argument(mm(FORCE), action='store_true', help='confirm change of existing date')
    kit_delete = kit_cmds.add_parser(DELETE, help='remove all entries for an item or group',
                                     description='remove all entries for an item or group')
    kit_delete.add_argument(NAME, help='item or group to delete')
    kit_delete.add_argument(mm(FORCE), action='store_true', help='confirm group deletion')
    kit_change = kit_cmds.add_parser(CHANGE, help='replace (or add) a part (wheel, innersole, etc)',
                                     description='replace (or add) a part (wheel, innersole, etc)')
    kit_change.add_argument(ITEM, help='item name (cotic, adidas, etc)')
    kit_change.add_argument(COMPONENT, help='component type (chain, laces, etc)')
    kit_change.add_argument(MODEL, help='model description')
    kit_change.add_argument(DATE, nargs='?', help='when changed (default now)')
    kit_change.add_argument(mm(FORCE), action='store_true', help='confirm creation of a new component')
    kit_change.add_argument(mm(START), action='store_true', help='set default date to start of item')
    kit_undo = kit_cmds.add_parser(UNDO, help='remove a change', description='remove a change')
    kit_undo.add_argument(ITEM, help='item name')
    kit_undo.add_argument(COMPONENT, help='component type')
    kit_undo.add_argument(MODEL, help='model description')
    kit_undo.add_argument(DATE, nargs='?', help='active date (to disambiguate models; default now)')
    kit_undo.add_argument(mm(ALL), action='store_true', help='remove all models (rather than single date)')
    kit_show = kit_cmds.add_parser(SHOW, help='display kit data',
                                   description='display kit data (show what stuff you use)')
    kit_show.add_argument(NAME, nargs='?', help='group or item to display (default all)')
    kit_show.add_argument(DATE, nargs='?', help='when to display (default now)')
    kit_show.add_argument(mm(CSV), action='store_true', help='CSV format')
    kit_statistics = kit_cmds.add_parser(STATISTICS, help='display statistics',
                                         description='display kit statistics')
    kit_statistics.add_argument(NAME, nargs='?', help='group, item, component or model')
    kit_statistics.add_argument(mm(CSV), action='store_true', help='CSV format')
    kit_rebuild = kit_cmds.add_parser(REBUILD, help='rebuild database entries')
    kit_dump = kit_cmds.add_parser(DUMP, help='dump to script')
    kit_dump.add_argument(mm(CMD), help='command to use instead of ch2')

    db = commands.add_parser(DB, help='configure the database')
    db_cmds = db.add_subparsers(title='sub-commands', dest=SUB_COMMAND, required=True)
    db_list = db_cmds.add_parser(LIST, help='show current configuration')
    db_list_item = db_list.add_subparsers(title='item to list', dest=ITEM, required=True)
    db_list_item.add_parser(USERS, help='show configured users')
    db_list_item.add_parser(SCHEMAS, help='show configured schema')
    db_list_item.add_parser(PROFILES, help='show available profiles')
    db_list_item.add_parser(DATABASES, help='show configured databases')
    db_add = db_cmds.add_parser(ADD, help='extend current configuration')
    db_add_item = db_add.add_subparsers(title='item to add', dest=ITEM, required=True)
    db_add_item.add_parser(USER, help='add a user (once per cluster)')
    db_add_item.add_parser(DATABASE, help='add a database (for each version in a cluster)')
    db_add_profile = db_add_item.add_parser(PROFILE, help='add a profile (for each user and version)')
    db_add_profile_profiles = db_add_profile.add_subparsers(title='profile', dest=PROFILE, required=True)
    from ..config.profile import get_profiles
    for name in get_profiles():
        db_add_profile_profiles.add_parser(name)
    db_backup = db_cmds.add_parser(BACKUP, help='backup current configuration')
    db_backup_item = db_backup.add_subparsers(title='item to backup', dest=ITEM, required=True)
    db_backup_item.add_parser(SCHEMA, help='backup a schema')
    db_remove = db_cmds.add_parser(REMOVE, help='reduce current configuration')
    db_remove_item = db_remove.add_subparsers(title='item to remove', dest=ITEM, required=True)
    db_remove_item.add_parser(USER, help='remove a user')
    db_remove_item.add_parser(DATABASE, help='remove a database')
    db_remove_schema = db_remove_item.add_parser(SCHEMA, help='remove a schema')
    db_remove_schema.add_argument(mm(no(PREVIOUS)), dest=PREVIOUS, action='store_false',
                                  help='do not create a :previous copy')

    import_ = commands.add_parser(IMPORT, help='import data from a previous version')
    import_.add_argument(SOURCE, nargs='?',
                         help='version or uri to import from '
                              '(version assumes same URI structure as current database); '
                              'omit to use latest version found locally')
    import_.add_argument(m(L), mm(LIST), action='store_true', help='list version found locally (and exit)')
    import_.add_argument(mm(DISABLE), action='store_true', help='disable following options (they enable by default)')
    import_.add_argument(mm(DIARY), action='store_true', help='enable (or disable) import of diary data')
    import_.add_argument(mm(ACTIVITIES), action='store_true', help='enable (or disable) import of activity data')
    import_.add_argument(mm(KIT), action='store_true', help='enable (or disable) import of kit data')
    import_.add_argument(mm(CONSTANTS), action='store_true', help='enable (or disable) import of constant data')
    import_.add_argument(mm(SEGMENTS), action='store_true', help='enable (or disable) import of segment data')

    delete = commands.add_parser(DELETE, help='delete an activity')
    delete.add_argument(DATE, help='date of activity to delete')

    fit = commands.add_parser(FIT, help='display contents of fit file')
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
        cmd.add_argument(mm(PATTERN), nargs='+', metavar='MSG:FLD[=VAL]', required=True,
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

    fix_fit = commands.add_parser(FIX_FIT, help='fix a corrupted fit file')
    fix_fit.add_argument(PATH, metavar='PATH', nargs='+', help='path to fit file')
    fix_fit.add_argument(m(W), mm(WARN), action='store_true', help='additional warning messages')
    fix_fit_output = fix_fit.add_argument_group(title='output (default hex to stdout)').add_mutually_exclusive_group()
    fix_fit_output.add_argument(m(O), mm(OUTPUT), help='output file for fixed data (otherwise, stdout)')
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

    thumbnail = commands.add_parser(THUMBNAIL, help='generate a thumbnail map of an activity')
    thumbnail.add_argument(ACTIVITY, type=int, metavar='ACTIVITY', help='an activity ID')
    add_image_dir(thumbnail)
    thumbnail.add_argument(mm(DISPLAY), action='store_true', help='display image')
    thumbnail.add_argument(mm(SECTOR), type=int, nargs='?', metavar='ID', help='mark sector')

    sparkline = commands.add_parser(SPARKLINE, help='generate a sparkline plot for a statistics')
    sparkline.add_argument(STATISTIC, type=int, metavar='STATISTIC', help='the statistics ID')
    add_image_dir(sparkline)
    sparkline.add_argument(mm(DISPLAY), action='store_true', help='display image')
    sparkline.add_argument(mm(ACTIVITY), type=int, nargs='?', metavar='ID', help='mark activity')

    if with_noop:
        noop = commands.add_parser(NO_OP, help='used within jupyter (no-op from cmd line)')

    package_fit_profile = commands.add_parser(PACKAGE_FIT_PROFILE,
                                                help='parse and save the global fit profile (dev only)')
    package_fit_profile.add_argument(PATH, metavar='PROFILE',
                                     help='the path to the profile (Profile.xlsx)')
    package_fit_profile.add_argument(m(W), mm(WARN), action='store_true',
                                     help='additional warning messages')

    show_schedule = commands.add_parser(SHOW_SCHEDULE, help='print schedule locations in a calendar')
    show_schedule.add_argument(SCHEDULE, metavar='SCHEDULE', help='schedule to test')
    show_schedule.add_argument(mm(START), metavar='DATE', help='date to start displaying data')
    show_schedule.add_argument(mm(MONTHS), metavar='N', type=int, help='number of months to display')

    return parser


def bootstrap_db(user, *args, configurator=None, post_config=None):

    from ..sql.config import Config
    # used in tests, given a base directory

    args = [mm(USER), user] + list(args)
    parser = make_parser()
    ns = NamespaceWithVariables._from_ns(parser.parse_args(args=args), PROGNAME, DB_VERSION)
    if configurator:
        data = Config(ns)
        configurator(data)
    args += post_config if post_config else []
    ns = NamespaceWithVariables._from_ns(parser.parse_args(args=args), PROGNAME, DB_VERSION)
    data = Config(ns)
    return data


def parse_pairs(pairs, convert=True, multi=False, comma=False):

    from ..lib import to_time

    # simple name, value pairs. owner and constraint supplied by command.
    d = {}
    if pairs is not None:
        for pair in pairs:
            name, value = pair.split('=', 1)
            if convert:
                for type in (int, float, to_time, lambda x: parse_bool(x, default=None)):
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


