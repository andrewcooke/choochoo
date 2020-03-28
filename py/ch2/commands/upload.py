
from hashlib import md5
from logging import getLogger
from os import makedirs
from os.path import basename, join, exists, dirname

from .activities import run_activity_pipelines
from .garmin import run_garmin
from .monitor import run_monitor_pipelines
from .statistics import run_statistic_pipelines
from ..diary.model import TYPE
from ..lib.log import log_current_exception
from ..commands.args import PATH, KIT, FAST
from ..lib.date import time_to_local_time, time_to_local_date, YMD, Y
from ..sql import KitItem, FileHash, Constant
from ..stats.names import TIME
from ..stats.read.activity import ActivityReader
from ..stats.read.monitor import MonitorReader


log = getLogger(__name__)


STREAM = 'stream'
DATA = 'data'
HASH = 'hash'
ACTIVITY = 'activity'
MONITOR = 'monitor'
SPORT = 'sport'
DIR = 'dir'

DATA_DIR = 'Data.Dir'
DOT_FIT = '.fit'


def upload(args, system, db):
    '''
## upload

    > ch2 upload --kit ITEM [ITEM...] -- PATH [PATH ...]

Upload activities from FIT files, storing the data in the file system and adding appropriate entries to the database.
Monitor data are also checked and loaded, and statistics updated.

### Examples

    > ch2 upload --kit cotic -- ~/fit/2018-01-01.fit

will store the given file, add activity data to the database (associated with the kit 'cotic'), check for
new monitor data, and update statistics.

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    files = open_files(args[PATH])
    upload_data(system, db, files=files, items=args[KIT], fast=args[FAST])


def open_files(paths):
    # converts a list of paths to a map of file names to file dicts with open streams
    files = {}
    for path in paths:
        name = basename(path)
        stream = open(path, 'rb')
        files[name] = {STREAM: stream}
    return files


def check_items(s, items):
    for item in items:
        if not s.query(KitItem).filter(KitItem.name == item).one_or_none():
            raise Exception(f'Kit item {item} does not exist')


def read_files(files):
    for name in files:
        file = files[name]
        log.debug(f'Reading {name}')
        file[DATA] = file[STREAM].read()


def hash_files(files):
    for name in files:
        file = files[name]
        log.debug(f'Hashing {name}')
        hash = md5()
        hash.update(file[DATA])
        file[HASH] = hash.hexdigest()
        log.debug(f'Hash of {name} is {file[HASH]}')


def check_files(s, files):
    for name in files:
        file = files[name]
        file_hash = s.query(FileHash).filter(FileHash.md5 == file[HASH]).one_or_none()
        if file_hash:
            if file_hash.activity_journal:
                raise Exception(f'File {name} is already associated with an activity on '
                                f'{time_to_local_time(file_hash.activity_journal.start)}')
            if file_hash.monitor_journal:
                raise Exception(f'File {name} is already associated with an monitor data for '
                                f'{time_to_local_time(file_hash.monitor_journal.start)}')


def get_fit_data(name, file, items=None):
    try:
        records = MonitorReader.parse_records(file[DATA])
        file[TIME] = MonitorReader.read_first_timestamp(name, records)
        file[TYPE] = MONITOR
        extra = ':' + file[HASH][0:5]
        log.debug(f'File {name} contains monitor data')
    except Exception as e:
        log_current_exception(traceback=False)
        records = ActivityReader.parse_records(file[DATA])
        file[TIME] = ActivityReader.read_first_timestamp(name, records)
        file[SPORT] = ActivityReader.read_sport(name, records)
        file[TYPE] = ACTIVITY
        extra = ':' + ','.join(items) if items else ''
        log.debug(f'File {name} contains activity data')
    return extra


def build_path(data_dir, item_path, file):
    date = time_to_local_date(file[TIME])
    file[DIR] = join(data_dir, file[TYPE], date.strftime(Y))
    if SPORT in file: file[DIR] = join(file[DIR], file[SPORT])
    file[PATH] = join(file[DIR], date.strftime(YMD) + item_path + DOT_FIT)
    log.debug(f'Target directory is {file[DIR]}')


def write_files(data_dir, files, items=None):
    for name in files:
        file = files[name]
        try:
            extra = get_fit_data(name, file, items)
        except Exception as e:
            log_current_exception(traceback=False)
            raise Exception(f'Could not parse {name} as a fit file')
        try:
            build_path(data_dir, extra, file)
            if not exists(file[DIR]):
                log.debug(f'Creating {file[DIR]}')
                makedirs(file[DIR])
            if exists(file[PATH]):
                log.warning(f'Overwriting data at {file[PATH]}')
            with open(file[PATH], 'wb') as out:
                log.debug(f'Writing {name} to {file[PATH]}')
                out.write(file[DATA])
        except Exception as e:
            log_current_exception(traceback=False)
            raise Exception(f'Could not save {name}')


def upload_data(sys, db, files=None, items=tuple(), fast=False):
    # this expects files to be a map from names to streams
    if files is None:
        files = {}
    with db.session_context() as s:
        data_dir = Constant.get_single(s, DATA_DIR)
        check_items(s, items)
        read_files(files)
        hash_files(files)
        check_files(s, files)
    write_files(data_dir, files, items)
    if not fast:
        run_activity_pipelines(sys, db)
        # run before and after so we know what exists before we update, and import what we read
        run_monitor_pipelines(sys, db)
        with db.session_context() as s:
            run_garmin(s)
        run_monitor_pipelines(sys, db)
        run_statistic_pipelines(sys, db)
