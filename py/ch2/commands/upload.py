
from glob import glob
from logging import getLogger
from os import makedirs, unlink
from os.path import basename, join, exists, dirname

from math import sqrt

from .activities import run_activity_pipelines
from .garmin import run_garmin
from .monitor import run_monitor_pipelines
from .statistics import run_statistic_pipelines
from ..commands.args import KIT, FAST, UPLOAD, BASE, FORCE, UNSAFE, DELETE, PATH, base_system_path, \
    PERMANENT, mm
from ..lib.date import time_to_local_time, Y, YMDTHMS
from ..lib.io import data_hash, split_fit_path, touch
from ..lib.log import log_current_exception, Record
from ..lib.utils import clean_path, slow_warning
from ..lib.workers import ProgressTree, SystemProgressTree
from ..pipeline.read.activity import ActivityReader
from ..pipeline.read.monitor import MonitorReader
from ..pipeline.read.utils import AbortImportButMarkScanned
from ..sql import KitItem, FileHash, ActivityJournal

log = getLogger(__name__)


TYPE = 'type'
TIME = 'time'
STREAM = 'stream'
DATA = 'data'
EXTRA = 'extra'
HASH = 'hash'
NAME = 'name'
ACTIVITY = 'activity'
MONITOR = 'monitor'
SPORT = 'sport'
DIR = 'dir'
DOT_FIT = '.fit'
READ_PATH = 'read-path'
WRITE_PATH = 'write-path'


def upload(args, system, db):
    '''
## upload

    > ch2 upload --kit ITEM [ITEM...] -- PATH [PATH ...]

Upload FIT files, storing the data in the permanent store (Data.Dir) on file system.
Optionally (if not --fast), scan the files and appropriate entries to the database.
Both monitor and activity files are accepted.

Files are checked for duplication on uploading (before being scanned).

If the uploaded file is mapped to a file path that already exists then we check the following cases:
* If the hash matches then the new data are discarded (duplicate).
* If the hash is different, it is an error (to avoid losing activity diary entries which are keyed by hash).

If the uploaded file has a hash that matches a file already read into the database, but the file path does not match,
then it is an error (internal error with inconsistent naming or duplicate data).

If --unsafe is given then files whose hashes match existing files are simply ignored.
This allows data downloaded en massed from Garmin to be uploaded ignoring already-uploaded data (with kit).

In short, hashes should map 1-to-1 to file names and to activities, and it is an error if they do not.

### Examples

    > ch2 upload --kit cotic -- ~/fit/2018-01-01.fit

will store the given file, add activity data to the database (associated with the kit 'cotic'), check for
new monitor data, and update statistics.

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    record = Record(log)
    nfiles, files = open_files(args[PATH])
    upload_files_and_update(record, system, db, args[BASE], files=files, nfiles=nfiles, force=args[FORCE],
                            items=args[KIT], fast=args[FAST], unsafe=args[UNSAFE], delete=args[DELETE])


class SkipFile(Exception):
    pass


def open_files(paths):
    # converts a list of paths to a map of file names to file dicts with open streams
    n = len(paths)

    def files():
        # use an iterator here to avoid opening too many files at once
        for path in paths:
            path = clean_path(path)
            if exists(path):
                name = basename(path)
                log.debug(f'Reading {path}')
                stream = open(path, 'rb')
                yield {STREAM: stream, NAME: name, READ_PATH: path}
            else:
                log.warning(f'File no longer exists at {path}')

    return n, files()


def check_items(s, items):
    for item in items:
        if not s.query(KitItem).filter(KitItem.name == item).one_or_none():
            raise Exception(f'Kit item {item} does not exist')


def read_file(file):
    # add DATA to dicts with STREAM
    log.debug(f'Reading {file[NAME]}')
    file[DATA] = file[STREAM].read()
    file[STREAM].close()


def hash_file(file):
    # add HASH to dicts with DATA
    log.debug(f'Hashing {file[NAME]}')
    file[HASH] = data_hash(file[DATA])
    log.debug(f'Hash of {file[NAME]} is {file[HASH]}')


def check_path(file, unsafe=False):
    path, name = file[WRITE_PATH], file[NAME]
    gpath, _ = split_fit_path(path)
    match = glob(gpath)
    if match:
        path2 = clean_path(match[0])
        log.debug(f'A file already exists at {path2}')
        with open(path2, 'rb') as input:
            hash = data_hash(input.read())
            if hash == file[HASH]:
                if path == path2:
                    # touch in case we deleted the activity and need to read again
                    touch(path)
                    raise SkipFile(f'Duplicate file {name} at {path2}')
                else:
                    # the base path is the same, and the hash is the same, but the kit has changed
                    # we probably want to delete the old file
                    log.warning(f'Will delete previous file at {path2} (replacing with {path})')
                    # we don't actually delete it, because what if write fails
                    file[DELETE] = path2
                    # continue processing because we need to write the new file
            else:
                msg = f'File {name} for {path} does not match the file already at {path2} (different hash or kit)'
                if unsafe:
                    raise SkipFile(msg)
                else:
                    raise Exception(msg)
    log.debug(f'File {name} cleared for path {path}')


def check_hash(s, file, unsafe=False):
    hash, path, name = file[HASH], file[WRITE_PATH], file[NAME]
    file_hash = s.query(FileHash).filter(FileHash.hash == hash).one_or_none()
    if file_hash and file_hash.file_scan:
        log.debug(f'A file was already scanned with hash {hash}')
        scanned_path = file_hash.file_scan.path
        if scanned_path == path:
            # touch in case we deleted the activity and need to read again
            touch(path)
            # should never happen because would be caught in check_path
            raise SkipFile(f'Duplicate file {name} at {path}')
        else:
            msg = f'File {name} for {path} matches the file already at {scanned_path} (same hash)'
            if unsafe:
                raise SkipFile(msg)
            else:
                raise Exception(msg)
    log.debug(f'File {name} cleared for hash {hash}')


def check_file(s, file, unsafe=False):
    check_path(file, unsafe=unsafe)
    check_hash(s, file, unsafe=unsafe)


def parse_fit_data(file, items=None):
    try:
        # add TIME and TYPE and EXTRA (and maybe SPORT) given (fit) DATA and NAME
        try:
            records = MonitorReader.parse_records(file[DATA])
            file[TIME] = MonitorReader.read_first_timestamp(file[NAME], records)
            file[TYPE] = MONITOR
            # don't use '-' here or it will be treated as kit in path matching
            file[EXTRA] = ':' + file[HASH][0:5]
            log.debug(f'File {file[NAME]} contains monitor data')
        except AbortImportButMarkScanned:
            records = ActivityReader.parse_records(file[DATA])
            file[TIME] = ActivityReader.read_first_timestamp(file[NAME], records)
            file[SPORT] = ActivityReader.read_sport(file[NAME], records)
            file[TYPE] = ACTIVITY
            file[EXTRA] = '-' + ','.join(items) if items else ''
            log.debug(f'File {file[NAME]} contains activity data')
    except Exception as e:
        log_current_exception(traceback=False)
        raise Exception(f'Could not parse {file[NAME]} as a fit file')


def build_path(data_dir, file):
    # add PATH given TIME, TYPE, SPORT and EXTRA
    date = time_to_local_time(file[TIME], fmt=YMDTHMS)
    year = time_to_local_time(file[TIME], fmt=Y)
    file[DIR] = join(data_dir, file[TYPE], year)
    if SPORT in file: file[DIR] = join(file[DIR], file[SPORT])
    file[WRITE_PATH] = join(file[DIR], date + file[EXTRA] + DOT_FIT)
    log.debug(f'Target directory is {file[DIR]}')


def write_file(file):
    try:
        dir = dirname(file[WRITE_PATH])
        if not exists(dir):
            log.debug(f'Creating {dir}')
            makedirs(dir)
        if exists(file[WRITE_PATH]):
            log.warning(f'Overwriting data at {file[WRITE_PATH]}')
        with open(file[WRITE_PATH], 'wb') as out:
            log.info(f'Writing {file[NAME]} to {file[WRITE_PATH]}')
            out.write(file[DATA])
    except Exception as e:
        log_current_exception(traceback=False)
        raise Exception(f'Could not save {file[NAME]}')


def delete_input_once_loaded(file, data_dir):
    if READ_PATH in file:
        if file[READ_PATH].startswith(data_dir):
            log.warning(f'Not deleting {file[NAME]} as located within Data.Dir ({file[READ_PATH]})')
        else:
            slow_warning(f'Deleting file {file[NAME]} from {file[READ_PATH]}', n=1, pause=0.001)
            unlink(file[READ_PATH])


def delete_old_kit(file):
    slow_warning(f'Deleting file {file[DELETE]} (changed kit)', n=1, pause=0.001)
    unlink(file[DELETE])


def upload_files(record, db, base, files=tuple(), nfiles=None, items=tuple(), progress=None,
                 unsafe=False, delete=False):
    try:
        local_progress = ProgressTree(len(files), parent=progress)
    except TypeError:
        local_progress = ProgressTree(nfiles, parent=progress)
    with record.record_exceptions():
        with db.session_context() as s:
            data_dir = base_system_path(base, version=PERMANENT)
            check_items(s, items)
            for file in files:
                with local_progress.increment_or_complete():
                    try:
                        read_file(file)
                        hash_file(file)
                        parse_fit_data(file, items=items)
                        build_path(data_dir, file)
                        check_file(s, file, unsafe=unsafe)
                        write_file(file)
                        record.info(f'Uploaded {file[NAME]} to {file[WRITE_PATH]}')
                        if delete: delete_input_once_loaded(file, data_dir)
                        if DELETE in file: delete_old_kit(file)
                    except SkipFile as e:
                        record.warning(e)
            local_progress.complete()  # catch no files case


def upload_files_and_update(record, sys, db, base, files=tuple(), nfiles=None, force=False, items=tuple(),
                            fast=False, unsafe=False, delete=False):
    # this expects files to be a list of maps from name to stream (or an iterator, if nfiles provided)
    if unsafe:
        record.warning('Unsafe option enabled')
    with db.session_context() as s:
        n = ActivityJournal.number_of_activities(s)
        weight = 1 if force else max(1, int(sqrt(n)))
        log.debug(f'Weight statistics as {weight} ({n} entries)')
    progress = ProgressTree(1) if fast else SystemProgressTree(sys, UPLOAD, [1] * 5 + [weight])
    log.info(f'Uploading files')
    upload_files(record, db, base, files=files, nfiles=nfiles, items=items, progress=progress,
                 unsafe=unsafe, delete=delete)
    # todo - add record to pipelines?
    if fast:
        log.info(f'{mm(FAST)} so upload finishing')
    else:
        log.info('Running activity pipelines')
        run_activity_pipelines(sys, db, base, force=force, progress=progress)
        # run before and after so we know what exists before we update, and import what we read
        log.info('Running monitor pipelines')
        run_monitor_pipelines(sys, db, base, force=force, progress=progress)
        with db.session_context() as s:
            try:
                log.info('Running Garmin download')
                run_garmin(sys, s, base=base, progress=progress)
            except Exception as e:
                log.warning(f'Could not get data from Garmin: {e}')
        log.info('Running monitor pipelines (again)')
        run_monitor_pipelines(sys, db, base, force=force, progress=progress)
        log.info('Running statistics pipelines')
        run_statistic_pipelines(sys, db, base, force=force, progress=progress)
