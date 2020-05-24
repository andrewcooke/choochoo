from logging import getLogger
import re

from . import copy_statistic_journal
from ...lib.log import log_current_exception
from ...sql import StatisticName, Constant, StatisticJournal

log = getLogger(__name__)


def upgrade_constant(record, old, new):
    if not constant_imported(record, new):
        with old.session_context() as old_s:
            copy_constants(record, old_s, old, new)
            list_missing_constants(record, new)


def constant_imported(record, new):
    with new.session_context() as new_s:
        # imported if NO undefined constants (more lenient than other imports)
        return not bool(new_s.query(Constant).
                        join(StatisticName).
                        outerjoin(StatisticJournal).
                        filter(StatisticJournal.id == None).count())


def list_missing_constants(record, new):
    with new.session_context() as new_s:
        for new_constant in new_s.query(Constant). \
                join(StatisticName). \
                outerjoin(StatisticJournal). \
                filter(StatisticJournal.id == None).all():
            record.warning(f'Constant {new_constant.name} still missing value(s)')


def copy_constants(record, old_s, old, new):
    constant = old.meta.tables['constant']
    for old_constant in old_s.query(constant).all():
        try:
            statistic_name = old.meta.tables['statistic_name']
            old_statistic_name = old_s.query(statistic_name). \
                filter(statistic_name.c.id == old_constant.statistic_name_id).one()
            with new.session_context() as new_s:
                old_name = old_constant.name.lower()
                new_constant = new_s.query(Constant).filter(Constant.name == old_name).one_or_none()
                for joint in (':', '_', '-'):
                    if not new_constant:
                        idx = old_name.rfind('.')
                        if idx != -1:
                            alternative = old_name[:idx] + joint + old_name[idx+1:]
                            log.debug(f'Retrying with {alternative}')
                            new_constant = new_s.query(Constant).filter(Constant.name == alternative).one_or_none()
                if new_constant:
                    copy_constant(record, old_s, old, old_constant, old_statistic_name, new_s, new_constant)
                else:
                    record.warning(f'No match for constant {old_constant.name}')
        except Exception as e:
            log_current_exception()
            record.warning(f'Error copying constant {old_constant.name}: {e}')


def copy_constant(record, old_s, old, old_constant, old_statistic_name, new_s, new_constant):
    missing = bool(new_s.query(Constant).
                   join(StatisticName).
                   outerjoin(StatisticJournal).
                   filter(Constant.id == new_constant.id,
                          StatisticJournal.id == None).count())
    if missing:
        statistic_journal = old.meta.tables['statistic_journal']
        for old_statistic_journal in old_s.query(statistic_journal). \
                filter(statistic_journal.c.source_id == old_constant.id,
                       statistic_journal.c.statistic_name_id == old_constant.statistic_name_id).all():
            copy_statistic_journal(record, old_s, old, old_statistic_name, old_statistic_journal,
                                   new_s, new_constant.statistic_name, new_constant, name=old_constant.name)
    else:
        record.warning(f'Constant {old_constant.name} already has values defined')
