from glob import glob
from logging import getLogger
from os.path import sep, exists, join, isfile, basename, dirname

from sqlalchemy.orm.exc import NoResultFound

from .args import SOURCE, ACTIVITY, DB_EXTN, DB_VERSION, base_system_path
from ..lib.date import format_date, time_to_local_date, to_time
from ..lib.log import log_current_exception
from ..lib.utils import clean_path
from ..sql.database import ReflectedDatabase, StatisticName, ActivityTopic, StatisticJournalType, \
    FileHash, ActivityTopicJournal, DiaryTopicJournal, DiaryTopic, StatisticJournal
from ..sql.tables.statistic import STATISTIC_JOURNAL_CLASSES
from ..sql.utils import add
from ..sql.types import short_cls


log = getLogger(__name__)


def import_(args, sys, db):
    '''
## import

    > ch2 import 0-30

Import diary entries from a previous version.
    '''
    import_path(Record(), args, args[SOURCE], db)


class Record:
    
    def __init__(self):
        self._warnings = []
        self._loaded = []
        
    def warning(self, msg):
        log.warning(msg)
        self._warnings.append(msg)
        
    def loaded(self, msg):
        log.info(msg)
        self._loaded.append(msg)

    def raise_(self, msg):
        self.warning(msg)
        raise Exception(msg)
        
    def json(self):
        return {'warnings': self._warnings,
                'loaded': self._loaded}


def import_path(record, base, source, new):
    path = build_source_path(record, base, source)
    old = ReflectedDatabase(path)
    if not old.meta.tables:
        record.raise_(f'No tables found in {path}')
    log.info(f'Importing data from {path}')
    import_diary(record, old, new)
    import_activity(record, old, new)


def build_source_path(record, base, source):
    database = ACTIVITY + DB_EXTN
    if sep not in source:
        path = base_system_path(base, file=database, version=source, create=False)
        if exists(path):
            log.info(f'{source} appears to be a version, using path {path}')
            return path
        else:
            log.warning(f'{source} is not a version ({path})')
    path = clean_path(source)
    if exists(path) and isfile(path):
        log.info(f'{source} exists at {path}')
        return path
    else:
        log.warning(f'{source} is not a database file ({path})')
    path = join(path, database)
    if exists(path) and isfile(path):
        log.info(f'{source} exists at {path}')
        return path
    else:
        log.warning(f'{source} is not a base directory ({path})')
    record.raise_(f'Could not find {source}')


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


def journal_imported(record, new, cls, name):
    # true if already installed
    with new.session_context() as new_s:
        if new_s.query(StatisticJournal). \
                join(cls). \
                filter(StatisticJournal.source_id == cls.id). \
                count():
            record.warning(f'{name} topic entries already exist - old data must be imported first')
            return True
    return False


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


def import_activity(record, old, new):
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


def match_statistic_name(record, old_statistic_name, new_s, owner, constraint):
    try:
        log.debug(f'Trying to find new statistic_name for {old_statistic_name}')
        new_statistic_name = new_s.query(StatisticName). \
                filter(StatisticName.name == old_statistic_name.name,
                       StatisticName.owner == owner,
                       StatisticName.constraint == constraint,
                       StatisticName.statistic_journal_type == old_statistic_name.statistic_journal_type).one()
        log.debug(f'Found new statistic_name {new_statistic_name}')
        return new_statistic_name
    except NoResultFound:
        record.raise_(f'No new equivalent to statistic {old_statistic_name.name} '
                      f'({StatisticJournalType(old_statistic_name.statistic_journal_type).name}) '
                      f'for {short_cls(owner)} / {constraint}')


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
        create_statistic_journal(record, old_s, old, old_statistic_name, old_statistic_journal,
                                 new_s, new_statistic_name, new_activity_topic_journal)


def create_activity_topic_journal(record, old_s, old, old_activity_topic_journal, new_s):
    log.debug(f'Trying to create activity_topic_journal')
    file_hash = old.meta.tables['file_hash']
    old_file_hash = old_s.query(file_hash). \
        filter(file_hash.c.id == old_activity_topic_journal.file_hash_id).one()
    log.debug(f'Found old file_hash {old_file_hash}')
    new_file_hash = FileHash.get_or_add(new_s, any_attr(old_file_hash, 'hash', 'md5'))
    log.debug(f'Found new file_hash {new_file_hash}')
    new_activity_topic_journal = ActivityTopicJournal.get_or_add(new_s, new_file_hash)
    log.debug(f'Found new activity_topic_journal {new_activity_topic_journal}')
    return new_activity_topic_journal


def create_statistic_journal(record, old_s, old, old_statistic_name, old_statistic_journal,
                             new_s, new_statistic_name, new_activity_topic_journal):
    journals = {StatisticJournalType.INTEGER.value: old.meta.tables['statistic_journal_integer'],
                StatisticJournalType.FLOAT.value: old.meta.tables['statistic_journal_float'],
                StatisticJournalType.TEXT.value: old.meta.tables['statistic_journal_text']}
    journal = journals[old_statistic_name.statistic_journal_type]
    old_value = old_s.query(journal).filter(journal.c.id == old_statistic_journal.id).one()
    log.debug(f'Resolved old statistic_journal {old_value}')
    new_value = add(new_s,
                    STATISTIC_JOURNAL_CLASSES[StatisticJournalType(new_statistic_name.statistic_journal_type)](
                        value=old_value.value, time=old_statistic_journal.time, statistic_name=new_statistic_name,
                        source=new_activity_topic_journal))
    date = format_date(time_to_local_date(to_time(new_value.time)))
    record.loaded(f'{new_value.value} at {date} for {new_statistic_name.name}')


def any_attr(instance, *names):
    log.debug(dir(instance))
    for name in names:
        if hasattr(instance, name):
            return getattr(instance, name)
    raise AttributeError(f'No {names} in {instance} ({type(instance)})')


def available_versions(base):
    versions = []
    if base.endswith(DB_VERSION): base = dirname(base)
    log.debug(f'Looking for previous versions under {base}')
    append(versions, (basename(candidate) for candidate in glob(join(base, '[0-9]-[0-9]*'))
                      if basename(candidate) != DB_VERSION))
    append(versions, glob(join(base, '**/database-[0-9]*-[0-9]*.sql'), recursive=True))
    append(versions, glob(join(base, '**/database-[0-9]*-[0-9]*.db'), recursive=True))
    return versions


def append(versions, glob):
    for version in sorted(glob, reverse=True):
        log.debug(version)
        versions.append(version)
