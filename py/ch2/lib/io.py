
from hashlib import md5
from logging import getLogger
from os import stat
from shutil import get_terminal_size

from sqlalchemy import desc

from .date import to_time
from ..sql.tables.file import FileScan, FileHash

log = getLogger(__name__)


def terminal_width(width=None):
    return get_terminal_size()[0] if width is None else width


def tui(command):
    def wrapper(*args, **kargs):
        return command(*args, **kargs)
    wrapper.tui = True
    wrapper.__doc__ = command.__doc__
    return wrapper


# https://stackoverflow.com/a/3431838
def md5_hash(file_path):
    hash = md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash.update(chunk)
    return hash.hexdigest()


def modified_file_scans(s, paths, owner, force=False):

    modified = []

    for path in paths:

        last_modified = to_time(stat(path).st_mtime)
        hash = md5_hash(path)
        file_scan_from_path = s.query(FileScan). \
            filter(FileScan.path == path,
                   FileScan.owner == owner).one_or_none()

        # get last scan and make sure it's up-to-date
        if file_scan_from_path:
            if hash != file_scan_from_path.file_hash.md5:
                log.warning('File at %s appears to have changed since last read on %s')
                file_scan_from_path.file_hash = FileHash.get_or_add(s, hash)
                file_scan_from_path.last_scan = 0.0
        else:
            # need to_time here because it's not roundtripped via the database to convert for use below
            file_scan_from_path = FileScan.add(s, path, owner, hash)
            s.flush()  # want this to appear in queries below

        # only look at hash if we are going to process anyway
        if force or last_modified > file_scan_from_path.last_scan:

            file_scan_from_hash = s.query(FileScan).\
                join(FileHash).\
                filter(FileHash.md5 == hash,
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
