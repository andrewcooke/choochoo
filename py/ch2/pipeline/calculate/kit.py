
from logging import getLogger

from .utils import MultiProcCalculator, ActivityJournalCalculatorMixin
from ..pipeline import OwnerInMixin
from ..read.activity import ActivityReader
from ...lib.log import log_current_exception
from ...sql import StatisticJournal, Timestamp
from ...sql.tables.kit import expand_item

log = getLogger(__name__)


class KitCalculator(OwnerInMixin, ActivityJournalCalculatorMixin, MultiProcCalculator):
    '''
    Convert `-D kit=XXX` statistic set on activities during import into kit usage entries.

    The kit statistic is also used directly by other code (eg to filter activities by kit).
    '''

    def _run_one(self, s, time):
        ajournal = self._get_source(s, time)
        with Timestamp(owner=self.owner_out, source=ajournal).on_success(s):
            kit = StatisticJournal.for_source(s, ajournal.id, ActivityReader.KIT, self.owner_in,
                                              ajournal.activity_group)
            if kit:
                log.debug(f'Read {kit.value} at {time} / {ajournal.activity_group.name}')
                for kit_name in kit.value.split(','):
                    try:
                        for kit_instance in expand_item(s, kit_name, ajournal.start):
                            kit_instance.add_use(s, ajournal.start, source=ajournal, owner=self.owner_out)
                            log.debug(f'Added usage for {kit_instance}')
                    except Exception as e:
                        log_current_exception()
                        log.warning(f'Could not add statistics for {kit_name}: {e}')
            else:
                log.debug(f'No kit defined for this activity ({time})')
