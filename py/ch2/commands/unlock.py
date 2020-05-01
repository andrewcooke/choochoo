
from logging import getLogger

from ..read.loader import StatisticJournalLoader

log = getLogger(__name__)


def unlock(args, system, db):
    '''
## unlock

    > ch2 unlock

Remove the "dummy" entry from the database that is used to coordinate locking across processes.

This should not be needed in normal use.  DO NOT use when worker processes are still running.
    '''
    with db.session_context() as s:
        log.info('Removing dummy entry...')
        StatisticJournalLoader.unlock(s)
        log.info('Removed (if present)')
