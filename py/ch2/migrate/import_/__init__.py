from glob import glob
from logging import getLogger
from os.path import dirname, basename, join

from sqlalchemy.orm.exc import NoResultFound

from ...commands.args import DB_VERSION
from ...lib import format_date, time_to_local_date, to_time
from ...sql import StatisticJournal, StatisticName, StatisticJournalType
from ...sql.tables.statistic import STATISTIC_JOURNAL_CLASSES
from ...sql.types import short_cls
from ...sql.utils import add

log = getLogger(__name__)


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


def copy_statistic_journal(record, old_s, old, old_statistic_name, old_statistic_journal,
                           new_s, new_statistic_name, source, name=None):
    journals = {StatisticJournalType.INTEGER.value: old.meta.tables['statistic_journal_integer'],
                StatisticJournalType.FLOAT.value: old.meta.tables['statistic_journal_float'],
                StatisticJournalType.TEXT.value: old.meta.tables['statistic_journal_text']}
    journal = journals[old_statistic_name.statistic_journal_type]
    old_value = old_s.query(journal).filter(journal.c.id == old_statistic_journal.id).one()
    log.debug(f'Resolved old statistic_journal {old_value}')
    new_value = add(new_s,
                    STATISTIC_JOURNAL_CLASSES[StatisticJournalType(new_statistic_name.statistic_journal_type)](
                        value=old_value.value, time=old_statistic_journal.time, statistic_name=new_statistic_name,
                        source=source))
    new_s.commit()  # avoid logging below if error
    date = format_date(time_to_local_date(to_time(new_value.time)))
    name = name if name else new_statistic_name.name
    record.loaded(f'Statistic {new_value.value} at {date} for {name}')


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
