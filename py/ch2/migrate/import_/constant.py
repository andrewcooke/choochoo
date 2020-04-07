from logging import getLogger

from ...lib import format_date, time_to_local_date, to_time
from ...sql import KitGroup, KitComponent, KitItem, KitModel, StatisticJournalTimestamp, StatisticName, \
    StatisticJournalType, Constant, StatisticJournal
from ...sql.utils import add
from ...stats.names import KIT_ADDED, KIT_RETIRED

log = getLogger(__name__)


def import_constant(record, old, new):
    if not constant_imported(record, new):
        with old.session_context() as old_s:
            with new.session_context() as new_s:
                # copy_components(record, old_s, old, new_s)
                # copy_tree(record, old_s, old, new_s)
                pass


def constant_imported(record, new):
    with new.session_context() as new_s:
        # imported if NO undefined constants (more lenient than other imports)
        return not bool(new_s.query(Constant).
                        join(StatisticName).
                        outerjoin(StatisticJournal).
                        filter(StatisticJournal.id == None).count())

#
# def copy_components(record, old_s, old, new_s):
#     component = old.meta.tables['kit_component']
#     for old_component in old_s.query(component).all():
#         add(new_s, KitComponent(name=old_component.name))
#         record.loaded(f'Component {old_component.name}')
#
