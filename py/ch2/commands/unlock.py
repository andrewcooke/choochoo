
from logging import getLogger

from ch2.pipeline.loader import SqliteLoader

log = getLogger(__name__)


def unlock(args, data):
    '''
## unlock

    > ch2 unlock

Remove the "dummy" entry from the database that is used to coordinate locking across processes.

This should not be needed in normal use.  DO NOT use when worker processes are still running.
    '''
    # todo - sqlite only
    with data.db.session_context() as s:
        log.info('Removing dummy entry...')
        SqliteLoader.unlock(s)
        log.info('Removed (if present)')
