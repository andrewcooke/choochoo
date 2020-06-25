from collections import defaultdict
from logging import getLogger
from os.path import sep, exists, join, isfile

from sqlalchemy_utils import database_exists

from .args import SOURCE, ACTIVITY, DB_EXTN, base_system_path, SEGMENTS, CONSTANTS, KIT, ACTIVITIES, DIARY, \
    infer_flags, ENGINE, SQLITE, POSTGRESQL, mm
from .read import DATA
from ..lib.log import Record
from ..lib.utils import clean_path
from ..import_.activity import import_activity
from ..import_.constant import import_constant
from ..import_.diary import import_diary
from ..import_.kit import import_kit
from ..import_.segment import import_segment
from ..sql.database import ReflectedDatabase, sqlite_uri, postgresql_uri, SystemConstant, scheme

log = getLogger(__name__)


def import_(args, data):
    '''
## import

    > ch2 import 0-30

Import data from a previous version (after starting a new version).
Data must be imported before any other changes are made to the database.

By default all types of data (diary, activities, kit, constants and segments) are imported.
Additional flags can enable or disable specific data types.

### Examples

    > ch2 import --diary 0-30

Import only diary entries.

    > ch2 import --disable --diary 0-30

Import everything but diary entries.
    '''
    flags = infer_flags(args, DIARY, ACTIVITIES, KIT, CONSTANTS, SEGMENTS)
    import_source(data, Record(log), args[SOURCE], flags=flags)


def infer_uri(data, source):
    if ':' in source:
        log.info(f'Using {source} directly as database URI for import')
        return source
    else:
        uri = data.get_uri(version=source, password='xxxxxx')
        log.info(f'Using {source} as a version number to get URI {uri}')
        return data.get_uri(version=source)



def import_source(data, record, source, engine=None, flags=None):
    # engine needed if source is not a URI
    with record.record_exceptions():
        uri = infer_uri(data, source)
        if flags is None: flags = defaultdict(lambda: True)
        old = ReflectedDatabase(uri)
        if not old.meta.tables:
            record.raise_(f'No tables found in {uri}')
        log.info(f'Importing data from {uri}')
        if flags[DIARY]: import_diary(record, old, data.db)
        if flags[ACTIVITIES]: import_activity(record, old, data.db)
        if flags[KIT]: import_kit(record, old, data.db)
        if flags[CONSTANTS]: import_constant(record, old, data.db)
        if flags[SEGMENTS]: import_segment(record, old, data.db)


def build_source_path(record, base, source):

    def nice_msg(template, source, path):
        msg = template
        if source != path: msg += f' ({path})'
        return msg

    database = ACTIVITY + DB_EXTN
    if sep not in source:
        path = base_system_path(base, subdir=DATA, file=database, version=source, create=False)
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


