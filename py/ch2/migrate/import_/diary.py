
from logging import getLogger

from sqlalchemy.orm.exc import NoResultFound

from . import journal_imported, match_statistic_name, create_statistic_journal
from ...sql import DiaryTopic, DiaryTopicJournal
from ...lib.log import log_current_exception

log = getLogger(__name__)


def import_diary(record, old, new):
    if not diary_imported(record, new):
        log.debug(f'Trying to copy diary topic data from {old} to {new}')
        with old.session_context() as old_s:
            diary_topic = old.meta.tables['diary_topic']
            for old_diary_topic in old_s.query(diary_topic).filter(diary_topic.c.parent_id == None).all():
                log.info(f'Found old (root) diary_topic {old_diary_topic}')
                copy_diary_topic_fields(record, old_s, old, old_diary_topic, new)


def diary_imported(record, new):
    return journal_imported(record, new, DiaryTopicJournal, 'Diary')


def copy_diary_topic_fields(record, old_s, old, old_diary_topic, new):
    try:
        with new.session_context() as new_s:
            try:
                new_diary_topic = new_s.query(DiaryTopic). \
                    filter(DiaryTopic.name == old_diary_topic.name,
                           DiaryTopic.schedule == old_diary_topic.schedule).one()
            except NoResultFound:
                record.raise_(f'No new equivalent to diary topic {old_diary_topic.name} '
                              f'(schedule {old_diary_topic.schedule})')
            constraint = str(new_diary_topic)
        copy_diary_topic_fields_with_constraint(record, old_s, old, old_diary_topic, new, constraint)
    except:
        log_current_exception()


def copy_diary_topic_fields_with_constraint(record, old_s, old, old_diary_topic, new, constraint):
    # this ignores the schedule on the diary_topic_field because it only copies statistics
    # i think this is ok?
    log.debug(f'Trying to copy diary_topic_fields for diary_topic {old_diary_topic}')
    diary_topic_field = old.meta.tables['diary_topic_field']
    for old_diary_topic_field in old_s.query(diary_topic_field). \
            filter(diary_topic_field.c.diary_topic_id ==
                   (old_diary_topic.id if old_diary_topic else None)).all():
        log.debug(f'Found old diary_topic_field {old_diary_topic_field}')
        try:
            statistic_name = old.meta.tables['statistic_name']
            old_statistic_name = old_s.query(statistic_name). \
                filter(statistic_name.c.id == old_diary_topic_field.statistic_name_id).one()
            log.debug(f'Found old statistic_name {old_statistic_name}')
            with new.session_context() as new_s:
                new_statistic_name = match_statistic_name(record, old_statistic_name, new_s, DiaryTopic, constraint)
                copy_diary_topic_journal_entries(record, old_s, old, old_statistic_name, new_s, new_statistic_name)
        except:
            log_current_exception()
    parent_id = old_diary_topic.id
    diary_topic = old.meta.tables['diary_topic']
    for old_diary_topic in old_s.query(diary_topic).filter(diary_topic.c.parent_id == parent_id).all():
        log.info(f'Found old diary_topic {old_diary_topic}')
        copy_diary_topic_fields(record, old_s, old, old_diary_topic, new)


def copy_diary_topic_journal_entries(record, old_s, old, old_statistic_name, new_s, new_statistic_name):
    log.debug(f'Trying to find statistic_journal entries for {old_statistic_name}')
    statistic_journal = old.meta.tables['statistic_journal']
    diary_topic_journal = old.meta.tables['diary_topic_journal']
    for old_statistic_journal in old_s.query(statistic_journal). \
            join(diary_topic_journal, statistic_journal.c.source_id == diary_topic_journal.c.id). \
            filter(statistic_journal.c.statistic_name_id == old_statistic_name.id).all():
        log.debug(f'Found old statistic_journal {old_statistic_journal}')
        old_diary_topic_journal = old_s.query(diary_topic_journal). \
            filter(diary_topic_journal.c.id == old_statistic_journal.source_id).one()
        log.debug(f'Found old diary_topic_journal {old_diary_topic_journal}')
        new_diary_topic_journal = DiaryTopicJournal.get_or_add(new_s, old_diary_topic_journal.date)
        log.debug(f'Found new diary_topic_journal {new_diary_topic_journal}')
        create_statistic_journal(record, old_s, old, old_statistic_name, old_statistic_journal,
                                 new_s, new_statistic_name, new_diary_topic_journal)


