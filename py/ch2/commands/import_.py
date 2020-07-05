from collections import defaultdict
from logging import getLogger

from .args import SOURCE, SEGMENTS, CONSTANTS, KIT, ACTIVITIES, DIARY, \
    infer_flags
from ..import_.activity import import_activity
from ..import_.constant import import_constant
from ..import_.diary import import_diary
from ..import_.kit import import_kit
from ..import_.segment import import_segment
from ..lib.log import Record
from ..sql.database import ReflectedDatabase

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
        safe_uri = data.get_safe_uri(version=source)
        log.info(f'Using {source} as a version number to get URI {safe_uri}')
        return data.get_uri(version=source)


def import_source(data, record, source, flags=None):
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
