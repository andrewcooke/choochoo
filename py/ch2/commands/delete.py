from logging import getLogger

from .args import DATE
from ..sql import ActivityJournal, FileScan

log = getLogger(__name__)


def delete(config):
    '''
## delete

    > ch2 delete 2020-01-01

Delete an activity from the database.
    '''
    with config.db.session_context() as s:
        activity = ActivityJournal.at(s, config.args[DATE])
        log.warning('Deleting file scan')
        s.query(FileScan).filter(FileScan.file_hash_id == activity.file_hash_id).delete()
        log.warning('Deleting activity')
        s.delete(activity)
        log.info('Done')
