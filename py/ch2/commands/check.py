from logging import getLogger

from .args import FIX
from ..lib.log import Record
from ..sql import ActivityTopicJournal, FileHash, FileScan, StatisticJournal

log = getLogger(__name__)


def check(args, system, db):
    '''
## check

    > ch2 check

This is still in development.
    '''
    record = Record(log)
    check_all(record, db, fix=args[FIX])


def check_all(record, db, fix=False):
    check_activity_diary(record, db, fix=fix)


def check_activity_diary(record, db, fix=False):
    check_activity_diary_missing_files(record, db, fix=fix)


def check_activity_diary_missing_files(record, db, fix=False):
    with record.record_exceptions(catch=True):
        with db.session_context() as s:
            bad = False
            for topic_journal in s.query(ActivityTopicJournal). \
                    join(StatisticJournal, StatisticJournal.source_id == ActivityTopicJournal.id). \
                    join(FileHash). \
                    outerjoin(FileScan). \
                    filter(FileScan.path == None).all():
                bad = True
                record.warning(f'{ActivityTopicJournal.__table__} with file hash '
                               f'{topic_journal.file_hash.hash[:6]} has associated entries but no activity')
                if fix:
                    record.warning('Deleting entry')
                    s.delete(topic_journal)
            if bad:
                record.info(f'Entries were deleted')
            else:
                record.info('No missing activities from activity topic data')



# add flag fix to fix things

# check everything needed for power estimates
# (including weight)

# check constants defined

# check configure was run (version)

# check whether permanent directory present

# check whether file system ok (space?)

# check whether all files are scanned

# check whether all activity topics entries have an activity for the file hash

# all activity diary entries have corresponding activity - fix group

# check for activity without GPS datya (lyn in 2018)

# check for multiple activiy topic journals (or whatever we have)
