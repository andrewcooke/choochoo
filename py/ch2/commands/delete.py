
from .args import DATE
from ..sql import ActivityJournal, FileScan


def delete(config):
    '''
## delete

    > ch2 delete 2020-01-01

Delete an activity from the database.
    '''
    with config.db.session_context() as s:
        activity = ActivityJournal.at(s, config.args[DATE])
        s.query(FileScan).filter(FileScan.file_hash_id == activity.file_hash_id).delete()
        s.delete(activity)
