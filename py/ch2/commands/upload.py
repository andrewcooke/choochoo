
from glob import glob
from logging import getLogger
from os import makedirs, unlink
from os.path import basename, join, exists

from math import sqrt

from .activities import run_activity_pipelines
from .garmin import run_garmin
from .monitor import run_monitor_pipelines
from .statistics import run_statistic_pipelines
from ..commands.args import KIT, FAST, UPLOAD, BASE, FORCE, UNSAFE, DELETE, PATH, REPLACE, mm
from ..diary.model import TYPE
from ..lib.date import time_to_local_time, Y, YMDTHMS
from ..lib.io import data_hash, split_fit_path
from ..lib.log import log_current_exception, Record
from ..lib.utils import clean_path, slow_warning
from ..lib.workers import ProgressTree, SystemProgressTree
from ..sql import KitItem, FileHash, Constant, ActivityJournal, Source, FileScan
from ..stats.names import TIME
from ..stats.read import AbortImportButMarkScanned
from ..stats.read.activity import ActivityReader
from ..stats.read.monitor import MonitorReader

log = getLogger(__name__)


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
REPLACES = 'replaces'

DATA_DIR = 'Data.Dir'


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
                            items=args[KIT], fast=args[FAST], unsafe=args[UNSAFE], delete=args[DELETE],
                            replace=[REPLACE])


class SkipFile(Exception):
    pass


def open_files(paths):
    # converts a list of paths to a map of file names to file dicts with open streams
    n = len(paths)

    def files():
        # use an iterator here to avoid opening too many files at once
        for path in paths:
            path = clean_path(path)
            name = basename(path)
            log.debug(f'Reading {path}')
            stream = open(path, 'rb')
            yield {STREAM: stream, NAME: name, READ_PATH: path}

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
            if hash == file[HASH] and path == path2:
                raise SkipFile(f'Duplicate file {name} at {path2}')
            elif REPLACES in file and path2 in file[REPLACES]:
                log.warning(f'Ignoring conflict at {path2} because {mm(REPLACE)}')
            else:
                msg = f'File {name} for {path} does not match the file already at {path2} (different hash or kit)'
                if unsafe:
                    raise SkipFile(msg)
                else:
                    raise Exception(msg)
    log.debug(f'File {name} cleared for path {path}')


def check_hash(s, file, unsafe):
    hash, path, name = file[HASH], file[WRITE_PATH], file[NAME]
    file_hash = s.query(FileHash).filter(FileHash.hash == hash).one_or_none()
    if file_hash and file_hash.file_scan:
        log.debug(f'A file was already scanned with hash {hash}')
        scanned_path = file_hash.file_scan.path
        if scanned_path == path:
            # should never happen because would be caught in check_path
            raise SkipFile(f'Duplicate file {name} at {path}')
        elif REPLACES in file and scanned_path in file[REPLACES]:
            log.warning(f'Ignoring conflict at {scanned_path} because {mm(REPLACE)}')
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


def remove_previous_activity(s, file):
    activity_journal = s.query(ActivityJournal).filter(ActivityJournal.start == file[TIME]).one_or_none()
    if not activity_journal:
        log.warning(f'No previous activity matching {file[NAME]}')
    else:
        # delete after reading (could be same as READ_PATH and we might fail to write)
        file[REPLACES] = [clean_path(row[0]) for row in
                          s.query(FileScan.path).join(FileHash).
                              filter(FileHash.id == activity_journal.file_hash_id).all()]
        log.debug(f'Found replacements {file[REPLACES]}')
        source = s.query(Source).filter(Source.id == activity_journal.id).one()
        slow_warning(f'Deleting activity at {time_to_local_time(activity_journal.start)}')
        s.delete(source)
        s.commit()


def remove_previous_files(file):
    if REPLACES in file:
        for path in file[REPLACES]:
            if path == file[WRITE_PATH]:
                log.warning(f'Not deleting {path} since wrote to same location ({mm(REPLACE)})')
            else:
                slow_warning(f'Deleting {path}')
                unlink(path)


def write_file(file):
    try:
        if not exists(file[DIR]):
            log.debug(f'Creating {file[DIR]}')
            makedirs(file[DIR])
        if exists(file[WRITE_PATH]):
            log.warning(f'Overwriting data at {file[WRITE_PATH]}')
        with open(file[WRITE_PATH], 'wb') as out:
            log.info(f'Writing {file[NAME]} to {file[WRITE_PATH]}')
            out.write(file[DATA])
    except Exception as e:
        log_current_exception(traceback=False)
        raise Exception(f'Could not save {file[NAME]}')


def delete_file(file, data_dir):
    if READ_PATH in file:
        if file[READ_PATH].startswith(data_dir):
            log.warning(f'Not deleting {file[NAME]} as located within Data.Dir ({file[READ_PATH]})')
        else:
            slow_warning(f'Deleting {file[NAME]} from {file[READ_PATH]}')
            unlink(file[READ_PATH])


def upload_files(record, db, files=tuple(), nfiles=None, items=tuple(), progress=None, unsafe=False, delete=False,
                 replace=False):
    try:
        local_progress = ProgressTree(len(files), parent=progress)
    except TypeError:
        local_progress = ProgressTree(nfiles, parent=progress)
    with record.record_exceptions():
        with db.session_context() as s:
            data_dir = clean_path(Constant.get_single(s, DATA_DIR))
            check_items(s, items)
            for file in files:
                with local_progress.increment_or_complete():
                    try:
                        read_file(file)
                        hash_file(file)
                        parse_fit_data(file, items=items)
                        build_path(data_dir, file)
                        if replace: remove_previous_activity(s, file)
                        check_file(s, file, unsafe)
                        write_file(file)
                        record.info(f'Uploaded {file[NAME]} to {file[WRITE_PATH]}')
                        if delete: delete_file(file, data_dir)
                        if replace: remove_previous_files(file)
                    except SkipFile as e:
                        record.warning(e)
            local_progress.complete()  # catch no files case


def upload_files_and_update(record, sys, db, base, files=tuple(), nfiles=None, force=False, items=tuple(),
                            fast=False, unsafe=False, delete=False, replace=False):
    # this expects files to be a list of maps from name to stream (or an iterator, if nfiles provided)
    if unsafe:
        record.warning('Unsafe option enabled')
    with db.session_context() as s:
        n = ActivityJournal.number_of_activities(s)
        weight = 1 if force else max(1, int(sqrt(n)))
        log.debug(f'Weight statistics as {weight} ({n} entries)')
    progress = ProgressTree(1) if fast else SystemProgressTree(sys, UPLOAD, [1] * 5 + [weight])
    upload_files(record, db, files=files, nfiles=nfiles, items=items, progress=progress, unsafe=unsafe, delete=delete,
                 replace=replace)
    # todo - add record to pipelines?
    if not fast:
        run_activity_pipelines(sys, db, base, force=force, progress=progress)
        # run before and after so we know what exists before we update, and import what we read
        run_monitor_pipelines(sys, db, base, force=force, progress=progress)
        with db.session_context() as s:
            try:
                run_garmin(sys, s, progress=progress)
            except Exception as e:
                log.warning(f'Could not get data from Garmin: {e}')
        run_monitor_pipelines(sys, db, base, force=force, progress=progress)
        run_statistic_pipelines(sys, db, base, force=force, progress=progress)
