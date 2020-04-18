from logging import getLogger

from sqlalchemy.orm import aliased

from ..lib.log import Record
from ..sql import ActivityTopicJournal, FileHash, FileScan, StatisticJournal, ActivityTopic, ActivityTopicField, \
    StatisticName, ActivityJournal, ActivityGroup

log = getLogger(__name__)


def check(args, system, db):
    '''
## check

    > ch2 check

This is still in development.
    '''
    record = Record(log)
    check_all(record, db)


def check_all(record, db):
    check_activity_diary(record, db)


def check_activity_diary(record, db):
    check_activity_diary_missing_files(record, db)
    check_activity_diary_inconsistent_groups(record, db)


def check_activity_diary_missing_files(record, db):
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
                for statistic in s.query(StatisticJournal). \
                        filter(StatisticJournal.source == topic_journal).all():
                    record.info(f"{statistic.statistic_name.name}: {statistic.value}")
            if bad:
                record.info(f'Manual fix: try to infer missing activity from entries and upload file')
            else:
                record.info('No missing activities from activity topic data')


def check_activity_diary_inconsistent_groups(record, db):
    with record.record_exceptions(catch=True):
        with db.session_context() as s:
            bad = False
            group_via_activity = aliased(ActivityGroup)
            group_via_topic = aliased(ActivityGroup)
            # this is tying journal entries to the activities and the topics.  since these are only
            # connected via file hash (since they need to persist across database reloads) they can
            # be inconsistent.
            for tjournal, agroup, tgroup, fscan in s.query(
                    ActivityTopicJournal, group_via_activity, group_via_topic, FileScan). \
                    join(StatisticJournal, StatisticJournal.source_id == ActivityTopicJournal.id). \
                    join(FileHash). \
                    join(FileScan). \
                    join(ActivityJournal, ActivityJournal.file_hash_id == FileHash.id). \
                    join(group_via_activity, ActivityJournal.activity_group_id == group_via_activity.id). \
                    join(StatisticName). \
                    join(ActivityTopicField). \
                    join(ActivityTopic). \
                    join(group_via_topic, ActivityTopic.activity_group_id == group_via_topic.id). \
                    filter(group_via_topic != group_via_activity).all():
                bad = True
                record.warning(f'{fscan.path} has {ActivityTopic.__table__} for {group_via_topic.name} but '
                               f'{ActivityJournal.__table__} for {group_via_activity.name}')
            if bad:
                record.info('Manual fix: rebuild with correct kit (if kit is determining activity group)')
            else:
                record.info('No inconsistent groups for activity topics')




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
