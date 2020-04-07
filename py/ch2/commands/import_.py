from logging import getLogger
from os.path import sep, exists, join, isfile

from .args import SOURCE, ACTIVITY, DB_EXTN, base_system_path
from ..lib.utils import clean_path
from ..migrate.import_ import Record
from ..migrate.import_.activity import import_activity
from ..migrate.import_.constant import import_constant
from ..migrate.import_.diary import import_diary
from ..migrate.import_.kit import import_kit
from ..sql.database import ReflectedDatabase

log = getLogger(__name__)


def import_(args, sys, db):
    '''
## import

    > ch2 import 0-30

Import diary entries from a previous version.
    '''
    import_path(Record(), args, args[SOURCE], db)


def import_path(record, base, source, new):
    path = build_source_path(record, base, source)
    old = ReflectedDatabase(path)
    if not old.meta.tables:
        record.raise_(f'No tables found in {path}')
    log.info(f'Importing data from {path}')
    import_diary(record, old, new)
    import_activity(record, old, new)
    import_kit(record, old, new)
    import_constant(record, old, new)


def build_source_path(record, base, source):
    database = ACTIVITY + DB_EXTN
    if sep not in source:
        path = base_system_path(base, file=database, version=source, create=False)
        if exists(path):
            log.info(f'{source} appears to be a version, using path {path}')
            return path
        else:
            log.warning(f'{source} is not a version ({path})')
    path = clean_path(source)
    if exists(path) and isfile(path):
        log.info(f'{source} exists at {path}')
        return path
    else:
        log.warning(f'{source} is not a database file ({path})')
    path = join(path, database)
    if exists(path) and isfile(path):
        log.info(f'{source} exists at {path}')
        return path
    else:
        log.warning(f'{source} is not a base directory ({path})')
    record.raise_(f'Could not find {source}')


