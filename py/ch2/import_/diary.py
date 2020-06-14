
from logging import getLogger

from sqlalchemy.orm.exc import MultipleResultsFound

from . import journal_imported, match_statistic_name, copy_statistic_journal, clone_with
from ..lib.log import log_current_exception
from ..sql import DiaryTopic, DiaryTopicJournal

log = getLogger(__name__)


def import_diary(record, old, new):
    if not diary_imported(record, new):
        record.info('Importing diary entries')
        log.debug(f'Trying to copy diary topic data from {old} to {new}')
        with old.session_context() as old_s:
            diary_topic = old.meta.tables['diary_topic']
            for old_diary_topic in old_s.query(diary_topic).filter(diary_topic.c.parent_id == None).all():
                log.info(f'Found old (root) diary_topic {old_diary_topic}')
                copy_diary_topic_fields(record, old_s, old, old_diary_topic, new)
    else:
        record.warning('Diary entries already imported')


def diary_imported(record, new):
    return journal_imported(record, new, DiaryTopicJournal, 'Diary', allow_time_zero=True)


def copy_diary_topic_fields(record, old_s, old, old_diary_topic, new):
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
            # changes for acooke config 0.31 - 0.32
            if old_statistic_name.name == 'Notes':
                if old_diary_topic.name == 'Multiple Sclerosis':
                    record.warning('Renaming Notes to MS Notes')
                    old_statistic_name = clone_with(old_statistic_name, name='MS Notes')
                elif old_diary_topic.name == 'Broken Femur LHS':
                    record.warning('Renaming Notes to Leg Notes')
                    old_statistic_name = clone_with(old_statistic_name, name='Leg Notes')
            with new.session_context() as new_s:
                try:
                    new_statistic_name = match_statistic_name(record, old_statistic_name, new_s, DiaryTopic)
                    copy_diary_topic_journal_entries(record, old_s, old, old_statistic_name, new_s, new_statistic_name)
                except MultipleResultsFound:
                    record.warning(f'Multiple statistics for {old_statistic_name} - '
                                   f'skipping field under topic {old_diary_topic}')
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
        copy_statistic_journal(record, old_s, old, old_statistic_name, old_statistic_journal,
                               new_s, new_statistic_name, new_diary_topic_journal)


