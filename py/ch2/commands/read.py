from collections import defaultdict
from glob import glob
from logging import getLogger
from os import makedirs
from os.path import basename, join, exists, dirname

from .calculate import run_statistic_pipelines
from .garmin import run_garmin
from ..commands.args import KIT, READ, FORCE, PATH, base_system_path, PERMANENT, WORKER, parse_pairs, \
    KARG, infer_flags, ACTIVITIES, CALCULATE
from ..common.date import time_to_local_time, Y, YMDTHMS
from ..common.io import touch, clean_path
from ..lib.io import data_hash, split_fit_path
from ..lib.log import log_current_exception, Record
from ..lib.workers import ProgressTree, SystemProgressTree
from ..pipeline.pipeline import run_pipeline
from ..pipeline.read.activity import ActivityReader
from ..pipeline.read.monitor import MonitorReader
from ..pipeline.read.utils import AbortImportButMarkScanned
from ..sql import KitItem, FileHash, PipelineType

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

FLAGS = (ACTIVITIES, MONITOR, CALCULATE)


def read(args, data):
    '''
## read

    > ch2 read --kit ITEM [ITEM...] -- PATH [PATH ...]

Read FIT files, storing the data in the permanent store on the file system,
then scan their contents, adding entries to the database, and finally calculating associated statistics.
Both monitor and activity files are accepted.

Scanning and calculation of activities can be disabled with --disable, and individual steps can
be enabled / disabled by name.

### Examples

    > ch2 read --kit cotic -- ~/fit/2018-01-01.fit

will store the given file, add activity data to the database (associated with the kit 'cotic'), check for
new monitor data, and update statistics.

    > ch2 read --calculate

is equivalent to `ch2 calculate` (so will not store and files, will not read data, but wil calculate statistics).

    > ch2 read --disable --calculate [PATH ...]

will read files and add their contents to the database, but not calculate statistics.

    > ch2 read --disable [PATH ...]

will read files (ie copy them to the permanent store), but do no other processing.

Note: When using bash use `shopt -s globstar` to enable ** globbing.
    '''
    if args[WORKER]:
        run_pipeline(data, None, paths=args[PATH], force=args[FORCE], worker=bool(args[WORKER]),
                     id=args[WORKER], **parse_pairs(args[KARG]))
    else:
        record = Record(log)
        flags = infer_flags(args, *FLAGS)
        nfiles, files = open_files(args[PATH])
        upload_files_and_update(record, data, files=files, nfiles=nfiles, force=args[FORCE],
                                items=args[KIT], flags=flags, **parse_pairs(args[KARG]))


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


def check_path(file):
    path, name = file[WRITE_PATH], file[NAME]
    gpath, _ = split_fit_path(path)
    match = glob(gpath)
    if match:
        touch(match[0])  # trigger re-processing
        raise SkipFile(f'A file already exists for {name} at {match[0]}')
    log.debug(f'File {name} cleared for path {path}')


def check_hash(s, file):
    hash, path, name = file[HASH], file[WRITE_PATH], file[NAME]
    file_hash = s.query(FileHash).filter(FileHash.hash == hash).one_or_none()
    if file_hash and file_hash.file_scan:
        raise SkipFile(f'A file was already processed with the same hash as {name} '
                       f'({hash} at {file_hash.file_scan.path})')
    log.debug(f'File {name} cleared for hash {hash}')


def check_file(s, file):
    check_path(file)
    check_hash(s, file)


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
        log_current_exception()
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
        log_current_exception()
        raise Exception(f'Could not save {file[NAME]}')


def upload_files(record, data, files=tuple(), nfiles=1, items=tuple(), progress=None):
    try:
        local_progress = ProgressTree(len(files), parent=progress)
    except TypeError:
        local_progress = ProgressTree(nfiles, parent=progress)
    with record.record_exceptions():
        with data.db.session_context() as s:
            data_dir = base_system_path(data.base, version=PERMANENT)
            check_items(s, items)
            for file in files:
                with local_progress.increment_or_complete():
                    try:
                        read_file(file)
                        hash_file(file)
                        parse_fit_data(file, items=items)
                        build_path(data_dir, file)
                        check_file(s, file)
                        write_file(file)
                        record.info(f'Uploaded {file[NAME]} to {file[WRITE_PATH]}')
                    except SkipFile as e:
                        record.warning(e)
            local_progress.complete()  # catch no files case


def upload_files_and_update(record, data, files=tuple(), nfiles=1, force=False, items=tuple(),
                            flags=None, **kargs):
    # this expects files to be a list of maps from name to stream (or an iterator, if nfiles provided)
    if not flags:
        flags = defaultdict(lambda: True)
    n_options = sum(1 if flags[name] else 0 for name in FLAGS)
    if flags[MONITOR]: n_options += 2
    progress = SystemProgressTree(data, READ, [1] * (n_options + 1))
    log.info(f'Uploading files')
    try:
        upload_files(record, data, files=files, nfiles=nfiles, items=items, progress=progress)
        # todo - add record to pipelines?
        if flags[ACTIVITIES]:
            log.info('Running activity pipelines')
            run_pipeline(data, PipelineType.READ_ACTIVITY, force=force, progress=progress, **kargs)
        if flags[MONITOR]:
            # run before and after so we know what exists before we update, and import what we read
            log.info('Running monitor pipelines')
            run_pipeline(data, PipelineType.READ_MONITOR, force=force, progress=progress, **kargs)
            with data.db.session_context() as s:
                try:
                    log.info('Running Garmin download')
                    run_garmin(data, s, base=data.base, progress=progress)
                except Exception as e:
                    log.warning(f'Could not get data from Garmin: {e}')
            log.info('Running monitor pipelines (again)')
            run_pipeline(data, PipelineType.READ_MONITOR, force=force, progress=progress, **kargs)
        if flags[CALCULATE]:
            log.info('Running statistics pipelines')
            run_statistic_pipelines(data, force=force, progress=progress, **kargs)
    finally:
        progress.complete()
