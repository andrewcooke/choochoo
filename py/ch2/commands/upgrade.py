from logging import getLogger
from os.path import sep, exists, join, isfile

from .args import SOURCE, ACTIVITY, DB_EXTN, base_system_path
from ..lib.utils import clean_path
from ..lib.log import Record
from ..migrate.import_.activity import upgrade_activity
from ..migrate.import_.constant import upgrade_constant
from ..migrate.import_.diary import upgrade_diary
from ..migrate.import_.kit import upgrade_kit
from ..sql.database import ReflectedDatabase

log = getLogger(__name__)


def upgrade(args, sys, db):
    '''
## import

    > ch2 import 0-30

Import diary entries from a previous version.
    '''
    upgrade_path(Record(log), args, args[SOURCE], db)


def upgrade_path(record, base, source, new):
    path = build_source_path(record, base, source)
    old = ReflectedDatabase(path, read_only=True)
    if not old.meta.tables:
        record.raise_(f'No tables found in {path}')
    log.info(f'Importing data from {path}')
    upgrade_diary(record, old, new)
    upgrade_activity(record, old, new)
    upgrade_kit(record, old, new)
    upgrade_constant(record, old, new)


def build_source_path(record, base, source):

    def nice_msg(template, source, path):
        msg = template
        if source != path: msg += f' ({path})'
        return msg

    database = ACTIVITY + DB_EXTN
    if sep not in source:
        path = base_system_path(base, file=database, version=source, create=False)
        if exists(path):
            log.info(nice_msg(f'{source} appears to be a version', source, path))
            return path
        else:
            log.warning(nice_msg(f'{source} is not a version', source, path))
    path = clean_path(source)
    if exists(path) and isfile(path):
        log.info(nice_msg(f'{source} exists', source, path))
        return path
    else:
        log.warning(f'{source} is not a database file ({path})')
    path = join(path, database)
    if exists(path) and isfile(path):
        log.info(nice_msg(f'{source} exists', source, path))
        return path
    else:
        log.warning(nice_msg(f'{source} is not a base directory', source, path))
    record.raise_(f'Could not find {source}')


