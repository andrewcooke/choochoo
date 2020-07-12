from collections import namedtuple
from logging import getLogger

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.exc import NoResultFound

from ..commands.args import DB_VERSION, URI_DEFAULT, URI_PREVIOUS
from ..lib import format_date, time_to_local_date, to_time
from ..sql import StatisticJournal, StatisticName, StatisticJournalType
from ..common.sql import database_really_exists
from ..sql.database import Database, CannotConnect
from ..sql.tables.statistic import STATISTIC_JOURNAL_CLASSES
from ..common.names import TIME_ZERO
from ..sql.types import short_cls
from ..sql.utils import add

log = getLogger(__name__)


def journal_imported(record, new, cls, name, allow_time_zero=False):
    # true if already installed
    with new.session_context() as new_s:
        q = new_s.query(StatisticJournal). \
            join(cls). \
            filter(StatisticJournal.source_id == cls.id)
        if allow_time_zero:
            q = q.filter(StatisticJournal.time > TIME_ZERO)
        if q.count():
            record.warning(f'{name} topic entries already exist - old data must be imported first')
            return True
    return False


def match_statistic_name(record, old_statistic_name, new_s, owner):
    try:
        log.debug(f'Trying to find new statistic_name for {old_statistic_name} ({owner})')
        new_statistic_name = new_s.query(StatisticName). \
            filter(StatisticName.name == old_statistic_name.name,
                   StatisticName.owner == owner,
                   StatisticName.statistic_journal_type == old_statistic_name.statistic_journal_type).one()
        log.debug(f'Found new statistic_name {new_statistic_name}')
        return new_statistic_name
    except NoResultFound:
        record.raise_(f'No new equivalent to statistic {old_statistic_name.name} '
                      f'({StatisticJournalType(old_statistic_name.statistic_journal_type).name}) '
                      f'for {short_cls(owner)}')


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
    previous = new_s.query(new_journal). \
        filter(new_journal.time == old_statistic_journal.time,
               new_journal.statistic_name == new_statistic_name).one_or_none()
    # drop ugly auto-titles if nicer ones available (bug fix 0-32 to 0-33)
    if previous and new_statistic_name.name == 'name' and \
            new_statistic_name.statistic_journal_type == StatisticJournalType.TEXT and \
            previous.value.startswith('20'):
        record.warning(f'Dropping previous ({previous}) for {name}')
        new_s.delete(previous)
        new_s.commit()
        previous = None
    if previous:
        record.warning(f'Value already exists for {name} ({previous})')
    else:
        new_value = add(new_s,
                        new_journal(value=old_value.value, time=old_statistic_journal.time,
                                    statistic_name=new_statistic_name, source=source))
        new_s.commit()  # avoid logging below if error
        date = format_date(time_to_local_date(to_time(new_value.time)))
        record.info(f'Statistic value {new_value.value} at {date} for {name}')


def any_attr(instance, *names):
    for name in names:
        if hasattr(instance, name):
            return getattr(instance, name)
    raise AttributeError(f'No {names} in {instance} ({type(instance)})')


def clone_with(result, **kargs):
    return namedtuple('clone', result._fields, defaults=result)(**kargs)


def available_versions(config, max_depth=3):
    return [version[1] for version in sorted(find_versions(config, max_depth=max_depth), reverse=True)]


def find_versions(config, max_depth=3):
    current_version = [int(version) for version in DB_VERSION.split('-')]
    for major, minor in count_down_version(current_version, max_depth=max_depth):
        version = f'{major}-{minor}'
        for uri_template in [URI_DEFAULT, URI_PREVIOUS]:
            if [major, minor] == current_version and uri_template == URI_DEFAULT: continue
            uri = config.args._with(version=version)._format(value=uri_template)
            log.debug(f'Trying uri {uri} for version {version}')
            try:
                db = Database(uri)
                if not db.no_data():
                    log.info(f'Import candidate for {version} at {uri_template}')
                    yield version, uri
            except CannotConnect:
                pass


def count_down_version(current_version, restart_minor=0, max_depth=3):
    major, minor = current_version
    while major >= 0:
        while minor >= 0 and max_depth > 0:
            yield major, minor
            minor -= 1
            max_depth -= 1
        minor = restart_minor
        major -= 1
