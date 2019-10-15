
from logging import getLogger

from . import MultiProcCalculator, ActivityJournalCalculatorMixin
from ...squeal import StatisticJournal
from ...squeal.tables.kit import expand_item

log = getLogger(__name__)


class KitCalculator(ActivityJournalCalculatorMixin, MultiProcCalculator):

    def _run_one(self, s, time):
        ajournal = self._get_source(s, time)
        kit = StatisticJournal.for_source(s, ajournal.id, 'kit', self.owner_in, ajournal.activity_group)
        if kit:
            log.debug(f'Read {kit.value}')
            for kit_name in kit.value.split(','):
                for kit_instance in expand_item(s, kit_name, ajournal.start):
                    kit_instance.add_use(s, ajournal.start, source=ajournal, owner=self.owner_out)
                    log.debug(f'Added usage for {kit_instance}')
        else:
            log.debug('No kit defined for this activity')

