
import re
from logging import getLogger
from os import stat
from shutil import get_terminal_size

from sqlalchemy import desc

import ch2.common.io
from ..common.date import to_time
from ..common.io import file_hash
from ..common.names import TIME_ZERO
from ..sql.tables.file import FileScan, FileHash

log = getLogger(__name__)


def terminal_width(width=None):
    width = get_terminal_size()[0] if width is None else width
    if width is None:
        log.warning('No terminal width available')
    else:
        log.debug(f'Terminal width is {width}')
    return width


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
                file_scan_from_path.last_scan = TIME_ZERO
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


