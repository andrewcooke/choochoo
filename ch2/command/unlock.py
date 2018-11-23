
from .args import FORCE
from ..squeal.tables.constant import SystemConstant


def unlock(args, log, db):
    '''
## unlock

    > ch2 unlock --force

Remove any locking.

The database is locked to allow fast loading of data which requires no other command access the database.
Using this command removes the lock and so MAY CAUSE DATA CORRUPTION if the loading is still in progress.

You should only use this command in the unlikely case that somehow the lock remained after the loading finished
(ie. if the system has a bug).
    '''
    if not args[FORCE]:
        raise Exception('See `ch2 help unlock`')
    log.warn('Removing any database lock(s).  This may cause data corruption.  See `ch2 help unlock`')
    with db.session_context() as s:
        SystemConstant.reset_lock(s)
        log.info('Lock reset')
