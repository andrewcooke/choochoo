import re
from collections import namedtuple
from glob import glob
from logging import getLogger
from os.path import dirname, basename, join

from sqlalchemy.orm.exc import NoResultFound

from ...commands.args import DB_VERSION
from ...names import ALL
from ...lib import format_date, time_to_local_date, to_time
from ...lib.utils import clean_path
from ...sql import StatisticJournal, StatisticName, StatisticJournalType, ActivityGroup
from ...sql.tables.statistic import STATISTIC_JOURNAL_CLASSES
from ...sql.types import short_cls
from ...sql.utils import add

log = getLogger(__name__)


def journal_imported(record, new, cls, name, allow_time_zero=False):
    # true if already installed
    with new.session_context() as new_s:
        q = new_s.query(StatisticJournal). \
                join(cls). \
                filter(StatisticJournal.source_id == cls.id)
        if allow_time_zero:
            q = q.filter(StatisticJournal.time > 0.0)
        if q.count():
            record.warning(f'{name} topic entries already exist - old data must be imported first')
            return True
    return False


def match_statistic_name(record, old_statistic_name, new_s, owner, activity_group):
    extract = re.compile('ActivityGroup "(.*)"')  # old style constraint
    if activity_group and extract.match(activity_group): activity_group = extract.match(activity_group).group(1)
    if not activity_group: activity_group = ALL
    try:
        log.debug(f'Trying to find new statistic_name for {old_statistic_name} ({owner})')
        new_statistic_name = new_s.query(StatisticName). \
            filter(StatisticName.name == old_statistic_name.name,
                   StatisticName.owner == owner,
                   StatisticName.activity_group == ActivityGroup.from_name(new_s, activity_group),
                   StatisticName.statistic_journal_type == old_statistic_name.statistic_journal_type).one()
        log.debug(f'Found new statistic_name {new_statistic_name}')
        return new_statistic_name
    except NoResultFound:
        record.raise_(f'No new equivalent to statistic {old_statistic_name.name} '
                      f'({StatisticJournalType(old_statistic_name.statistic_journal_type).name}) '
                      f'for {short_cls(owner)} / {activity_group}')


def copy_statistic_journal(record, old_s, old, old_statistic_name, old_statistic_journal,
                           new_s, new_statistic_name, source, name=None):
    name = name if name else new_statistic_name.name
    old_journals = {StatisticJournalType.INTEGER.value: old.meta.tables['statistic_journal_integer'],
                    StatisticJournalType.FLOAT.value: old.meta.tables['statistic_journal_float'],
                    StatisticJournalType.TEXT.value: old.meta.tables['statistic_journal_text']}
    old_journal = old_journals[old_statistic_name.statistic_journal_type]
    old_value = old_s.query(old_journal).filter(old_journal.c.id == old_statistic_journal.id).one()
    log.debug(f'Resolved old statistic_journal {old_value}')
    new_journal = STATISTIC_JOURNAL_CLASSES[StatisticJournalType(new_statistic_name.statistic_journal_type)]
    if new_s.query(new_journal). \
            filter(new_journal.time == old_statistic_journal.time,
                   new_journal.statistic_name == new_statistic_name).count():
        log.warning(f'Value already exists for {name}')
    else:
        new_value = add(new_s,
                        new_journal(value=old_value.value, time=old_statistic_journal.time,
                                    statistic_name=new_statistic_name, source=source))
        new_s.commit()  # avoid logging below if error
        date = format_date(time_to_local_date(to_time(new_value.time)))
        record.info(f'Statistic {new_value.value} at {date} for {name}')


def any_attr(instance, *names):
    for name in names:
        if hasattr(instance, name):
            return getattr(instance, name)
    raise AttributeError(f'No {names} in {instance} ({type(instance)})')


def available_versions(base):
    versions = []
    base = clean_path(base)
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


def clone_with(result, **kargs):
    return namedtuple('clone', result._fields, defaults=result)(**kargs)
