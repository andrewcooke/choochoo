from logging import getLogger

from sqlalchemy.orm import aliased
from sqlalchemy.sql.functions import func

from ..data.names import ALL
from ..lib import time_to_local_time
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
    check_inconsistent_groups_activity_journal_v_topic(record, db)
    check_inconsistent_groups_activity_journal_v_topic_statistics(record, db)
    check_activity_topic_multiple_groups(record, db)


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


def check_inconsistent_groups_activity_journal_v_topic(record, db):
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


def check_inconsistent_groups_activity_journal_v_topic_statistics(record, db):
    with record.record_exceptions(catch=True):
        with db.session_context() as s:
            q = s.query(StatisticName, ActivityJournal, StatisticJournal). \
                join(StatisticJournal, StatisticJournal.statistic_name_id == StatisticName.id). \
                join(ActivityTopicJournal, StatisticJournal.source_id == ActivityTopicJournal.id). \
                join(ActivityJournal, ActivityTopicJournal.file_hash_id == ActivityJournal.file_hash_id). \
                filter(StatisticName.activity_group_id != ActivityJournal.activity_group_id). \
                order_by(ActivityJournal.start)
            # log.debug(q)
            for name, activity, journal in q.all():
                q = s.query(StatisticJournal). \
                    join(StatisticName, StatisticName.id == StatisticJournal.statistic_name_id). \
                    join(ActivityTopicJournal, StatisticJournal.source_id == ActivityTopicJournal.id). \
                    join(ActivityJournal, ActivityJournal.file_hash_id == ActivityTopicJournal.file_hash_id). \
                    filter(StatisticName.name == name.name,
                           StatisticName.activity_group_id == ActivityJournal.activity_group_id,
                           ActivityJournal.id == activity.id)
                # log.debug(q)
                alternate = q.one_or_none()
                if alternate:
                    record.warning(f'Activity on {time_to_local_time(activity.start)} '
                                   f'for group {activity.activity_group.name} '
                                   f'is associated with journal statistic {name.name} '
                                   f'for group {name.activity_group.name} '
                                   f'with value {journal.value} and correct alternative {alternate.value}')
                else:
                    record.warning(f'Activity on {time_to_local_time(activity.start)} '
                                   f'for group {activity.activity_group.name} '
                                   f'is associated with journal statistic {name.name} '
                                   f'for group {name.activity_group.name} '
                                   f'with value {journal.value} and no alternative')


def check_activity_topic_multiple_groups(record, db):
    with record.record_exceptions(catch=True):
        with db.session_context() as s:
            q = s.query(func.group_concat(ActivityGroup.name.distinct()), ActivityTopicJournal). \
                join(StatisticJournal, StatisticJournal.source_id == ActivityTopicJournal.id). \
                join(StatisticName, StatisticName.id == StatisticJournal.statistic_name_id). \
                filter(ActivityGroup.id == StatisticName.activity_group_id,
                       ActivityTopicJournal.file_hash_id == ActivityJournal.file_hash_id,
                       ActivityGroup.name != ALL). \
                group_by(ActivityTopicJournal)
            log.debug(q)
            # tried to query journal as well as topic and hit sqlalchemy bug, so order in python
            all = sorted(q.all(), key=lambda x: x[1].file_hash.activity_journal.start)
            for (groups, topic) in all:
                journal = topic.file_hash.activity_journal
                if ',' in groups:
                    record.warning(f'Activity topic journal for {time_to_local_time(journal.start)} '
                                   f'is associated with multiple groups: {groups}')

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
