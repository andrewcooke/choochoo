
import re
from hashlib import md5
from logging import getLogger
from os import stat
from pathlib import Path
from shutil import get_terminal_size

from sqlalchemy import desc

from .date import to_time
from ..sql.tables.file import FileScan, FileHash


log = getLogger(__name__)


def terminal_width(width=None):
    width = get_terminal_size()[0] if width is None else width
    if width is None:
        log.warning('No terminal width available')
    else:
        log.debug(f'Terminal width is {width}')
    return width


# https://stackoverflow.com/a/3431838
def file_hash(file_path):
    hash = md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash.update(chunk)
    return hash.hexdigest()


def data_hash(data):
    if isinstance(data, str): data = data.encode('utf-8')
    hash = md5()
    hash.update(data)
    return hash.hexdigest()


def modified_file_scans(s, paths, owner, force=False):

    modified = []

    for path in paths:

        # log.debug(f'Scanning {path}')
        last_modified = to_time(stat(path).st_mtime)
        hash = file_hash(path)
        file_scan_from_path = s.query(FileScan). \
            filter(FileScan.path == path,
                   FileScan.owner == owner).one_or_none()

        # get last scan and make sure it's up-to-date
        if file_scan_from_path:
            if hash != file_scan_from_path.file_hash.hash:
                log.warning('File at %s appears to have changed since last read on %s')
                file_scan_from_path.file_hash = FileHash.get_or_add(s, hash)
                file_scan_from_path.last_scan = 0.0
        else:
            file_scan_from_path = FileScan.add(s, path, owner, hash)
            s.flush()  # want this to appear in queries below

        # only look at hash if we are going to process anyway
        if force or last_modified > file_scan_from_path.last_scan:

            file_scan_from_hash = s.query(FileScan).\
                join(FileHash).\
                filter(FileHash.hash == hash,
                       FileScan.owner == owner).\
                order_by(desc(FileScan.last_scan)).limit(1).one()  # must exist as file_scan_from_path is a candidate
            if file_scan_from_hash.path != file_scan_from_path.path:
                log.warning('Ignoring duplicate file (details in debug log)')
                log.debug('%s' % file_scan_from_path.path)
                log.debug('%s' % file_scan_from_hash.path)
                # update the path to avoid triggering in future
                file_scan_from_path.last_scan = file_scan_from_hash.last_scan

            if force or last_modified > file_scan_from_hash.last_scan:
                modified.append(file_scan_from_hash)

    s.commit()
    return modified


def split_fit_path(path):
    # returns glob and kit
    pattern = re.compile(r'(.*\d\d\d\d-\d\d-\d\d.*)-([\w,]+).fit')
    match = pattern.match(path)
    if match:
        return match.group(1) + '*.fit', match.group(2)
    else:
        return path[:-4] + '*' + path[-4:], None


def touch(path):
    Path(path).touch()
