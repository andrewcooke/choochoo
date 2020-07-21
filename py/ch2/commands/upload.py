from glob import glob
from glob import glob
from logging import getLogger
from os import makedirs
from os.path import basename, join, exists, dirname

from ..commands.args import KIT, PATH, DATA_DIR, UPLOAD, PROCESS, FORCE
from ..common.date import time_to_local_time, Y, YMDTHMS
from ..common.io import touch, clean_path, data_hash
from ..common.log import log_current_exception
from ..lib.io import split_fit_path
from ..lib.log import Record
from ..lib.utils import timing
from ..lib.workers import ProgressTree
from ..pipeline.process import run_pipeline
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


def upload(config):
    '''
## upload

    > ch2 upload --kit ITEM [ITEM...] -- PATH [PATH ...]

Copy FIT files, storing the data in the permanent store on the file system.
Optionally, call process after, to add data to the database.
Both monitor and activity files are accepted.

### Examples

    > ch2 upload --kit cotic -- ~/fit/2018-01-01.fit

will store the given file, add activity data to the database (associated with the kit 'cotic'), check for
new monitor data, and update statistics.
    '''
    args = config.args
    nfiles, files = open_files(args[PATH])
    with timing(UPLOAD):
        upload_files(Record(log), config, files=files, nfiles=nfiles, items=args[KIT])
        if args[PROCESS]:
            run_pipeline(config, PipelineType.PROCESS, force=args[FORCE])


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
    from ch2.pipeline.read.monitor import MonitorReader
    from ch2.pipeline.read.activity import ActivityReader
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
            data_dir = data.args._format_path(DATA_DIR)
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
