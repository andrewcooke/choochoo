
import re
from logging import getLogger
from os import stat

from sqlalchemy import desc

from ..common.date import to_time
from ..common.io import file_hash
from ..common.names import TIME_ZERO
from ..sql.tables.file import FileScan, FileHash

log = getLogger(__name__)


def modified_file_scans(s, paths, owner):

    modified = []

    for path in paths:

        # log.debug(f'Scanning {path}')
        last_modified = to_time(stat(path).st_mtime)
        hash = file_hash(path)
        file_scan_from_hash = s.query(FileScan).\
            join(FileHash).\
            filter(FileHash.hash == hash,
                   FileScan.owner == owner).one_or_none()
        file_scan_from_path = s.query(FileScan). \
            filter(FileScan.path == path,
                   FileScan.owner == owner).one_or_none()

        # get last scan and make sure it's up-to-date
        if file_scan_from_path:
            if hash != file_scan_from_path.file_hash.hash:
                log.warning(f'File at {path} appears to have changed since last read on '
                            f'{file_scan_from_path.last_scan}')
                file_scan_from_path.file_hash = FileHash.get_or_add(s, hash)
                file_scan_from_path.last_scan = TIME_ZERO
        elif file_scan_from_hash:
            log.warning(f'File at {path} already exists at {file_scan_from_hash} - skipping')
            continue
        else:
            file_scan_from_path = FileScan.add(s, path, owner, hash)
            s.flush()  # want this to appear in queries below

        # only look at hash if we are going to process anyway
        if last_modified > file_scan_from_path.last_scan:

            log.debug(f'File at {path} was modified on {last_modified} '
                      f'which is after last read on {file_scan_from_path.last_scan}')

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

            if last_modified > file_scan_from_hash.last_scan:
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


