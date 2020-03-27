from hashlib import md5
from logging import getLogger
from os.path import basename, join

from ..lib.log import log_current_exception
from ..commands.args import PATH, KIT
from ..lib.date import time_to_local_time, time_to_local_date, YMD, Y
from ..sql import KitItem, FileHash, Constant
from ..stats.read.activity import ActivityReader


log = getLogger(__name__)

STREAM = 'stream'
DATA = 'data'
HASH = 'hash'

UPLOAD_DIR = 'Upload.Dir'


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
    upload_data(files=files, items=args[KIT])


def open_files(paths):
    # converts a list of paths to a map of file names to streams
    files = {}
    for path in paths:
        name = basename(path)
        stream = open(path, 'r')
        files[name] = stream
    return files


def check_items(s, items):
    for item in items:
        if not s.query(KitItem).filter(KitItem.name == item).one_or_none():
            raise Exception(f'Kit item {item} does not exist')


def check_files(s, files):
    # extends map with DATA and HASH
    for name in files:
        file = files[name]
        file[DATA] = file[STREAM].read()
        hash = md5()
        hash.update(file[DATA])
        file[HASH] = hash.hexdigest()
        file_hash = s.query(FileHash).filter(FileHash.md5 == file[HASH]).one_or_none()
        if file_hash:
            if file_hash.activity_journal:
                raise Exception(f'File {name} is already associated with an activity on '
                                f'{time_to_local_time(file_hash.activity_journal.start)}')
            if file_hash.monitor_journal:
                raise Exception(f'File {name} is already associated with an monitor data for '
                                f'{time_to_local_time(file_hash.monitor_journal.start)}')


def write_files(s, items, files):
    try:
        dir = Constant.get(s, UPLOAD_DIR).at(s)
    except Exception as e:
        log_current_exception()
        raise Exception(f'{UPLOAD_DIR} is not configured')
    item_path = '-' + '-'.join(items) if items else ''
    for name in files:
        file = files[name]
        try:
            records = ActivityReader.read_records(file[DATA])
            sport = ActivityReader.read_sport(name, records)
            time = ActivityReader.read_first_timestamp(name, records)
        except Exception as e:
            log_current_exception()
            raise Exception(f'Could not parse {name} as a fit file')
        try:
            date = time_to_local_date(time)
            file[PATH] = join(dir, date.strftime(Y), sport, date.strftime(YMD) + item_path + '.fit')
            with open(file[PATH], 'wb') as out:
                log.debug(f'Writing {name} to {file[PATH]}')
                out.write(file[DATA])
        except Exception as e:
            log_current_exception()
            raise Exception(f'Could not save {name} to {file[PATH]}')


def upload_data(sys, db, files=None, items=tuple()):
    # this expects files to be a map from names to streams
    if files is None:
        files = {}
    with db.session_context() as s:
        check_items(s, items)
        check_files(s, files)
        write_files(s, items, files)
