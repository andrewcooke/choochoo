
from logging import getLogger

from . import journal_imported, match_statistic_name, copy_statistic_journal, any_attr
from ...lib.log import log_current_exception
from ...sql import ActivityTopicJournal, FileHash, ActivityTopic

log = getLogger(__name__)


def upgrade_activity(record, old, new):
    if not activity_imported(record, new):
        log.debug(f'Trying to copy activity topic data from {old} to {new}')
        with old.session_context() as old_s:
            copy_activity_topic_fields(record, old_s, old, None, new)
            activity_topic = old.meta.tables['activity_topic']
            for old_activity_topic in old_s.query(activity_topic).filter(activity_topic.c.parent_id == None).all():
                log.info(f'Found old (root) activity_topic {old_activity_topic}')
                copy_activity_topic_fields(record, old_s, old, old_activity_topic, new)


def activity_imported(record, new):
    return journal_imported(record, new, ActivityTopicJournal, 'Activity')


def copy_activity_topic_fields(record, old_s, old, old_activity_topic, new):
    log.debug(f'Trying to copy activity_topic_fields for activity_topic {old_activity_topic}')
    activity_topic_field = old.meta.tables['activity_topic_field']
    for old_activity_topic_field in old_s.query(activity_topic_field). \
            filter(activity_topic_field.c.activity_topic_id ==
                   (old_activity_topic.id if old_activity_topic else None)).all():
        log.debug(f'Found old activity_topic_field {old_activity_topic_field}')
        try:
            statistic_name = old.meta.tables['statistic_name']
            old_statistic_name = old_s.query(statistic_name). \
                filter(statistic_name.c.id == old_activity_topic_field.statistic_name_id).one()
            log.debug(f'Found old statistic_name {old_statistic_name}')
            with new.session_context() as new_s:
                new_statistic_name = match_statistic_name(record, old_statistic_name, new_s, ActivityTopic,
                                                          old_statistic_name.constraint)
                copy_activity_topic_journal_entries(record, old_s, old, old_statistic_name, new_s, new_statistic_name)
        except:
            log_current_exception()
    if old_activity_topic:
        parent_id = old_activity_topic.id
        activity_topic = old.meta.tables['activity_topic']
        for old_activity_topic in old_s.query(activity_topic).filter(activity_topic.c.parent_id == parent_id).all():
            log.info(f'Found old activity_topic {old_activity_topic}')
            copy_activity_topic_fields(record, old_s, old, old_activity_topic, new)


def copy_activity_topic_journal_entries(record, old_s, old, old_statistic_name, new_s, new_statistic_name):
    log.debug(f'Trying to find statistic_journal entries for {old_statistic_name}')
    statistic_journal = old.meta.tables['statistic_journal']
    activity_topic_journal = old.meta.tables['activity_topic_journal']
    for old_statistic_journal in old_s.query(statistic_journal). \
            join(activity_topic_journal, statistic_journal.c.source_id == activity_topic_journal.c.id). \
            filter(statistic_journal.c.statistic_name_id == old_statistic_name.id).all():
        log.debug(f'Found old statistic_journal {old_statistic_journal}')
        old_activity_topic_journal = old_s.query(activity_topic_journal). \
            filter(activity_topic_journal.c.id == old_statistic_journal.source_id).one()
        log.debug(f'Found old activity_topic_journal {old_activity_topic_journal}')
        new_activity_topic_journal = create_activity_topic_journal(record, old_s, old, old_activity_topic_journal, new_s)
        copy_statistic_journal(record, old_s, old, old_statistic_name, old_statistic_journal,
                               new_s, new_statistic_name, new_activity_topic_journal)


def create_activity_topic_journal(record, old_s, old, old_activity_topic_journal, new_s):
    log.debug(f'Trying to create activity_topic_journal')
    file_hash = old.meta.tables['file_hash']
    old_file_hash = old_s.query(file_hash). \
        filter(file_hash.c.id == old_activity_topic_journal.file_hash_id).one()
    log.debug(f'Found old file_hash {old_file_hash}')
    # column name change 0-29 - 0-30 ?
    new_file_hash = FileHash.get_or_add(new_s, any_attr(old_file_hash, 'hash', 'md5'))
    log.debug(f'Found new file_hash {new_file_hash}')
    new_activity_topic_journal = ActivityTopicJournal.get_or_add(new_s, new_file_hash)
    log.debug(f'Found new activity_topic_journal {new_activity_topic_journal}')
    return new_activity_topic_journal
