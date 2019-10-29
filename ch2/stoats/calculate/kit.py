
from logging import getLogger

from . import MultiProcCalculator, ActivityJournalCalculatorMixin
from ...squeal import StatisticJournal, Timestamp
from ...squeal.tables.kit import expand_item

log = getLogger(__name__)


class KitCalculator(ActivityJournalCalculatorMixin, MultiProcCalculator):

    def _run_one(self, s, time):
        ajournal = self._get_source(s, time)
        with Timestamp(owner=self.owner_out, source=ajournal).on_success(s):
            kit = StatisticJournal.for_source(s, ajournal.id, 'kit', self.owner_in, ajournal.activity_group)
            if kit:
                log.debug(f'Read {kit.value} at {time} / {ajournal.activity_group.name}')
                for kit_name in kit.value.split(','):
                    for kit_instance in expand_item(s, kit_name, ajournal.start):
                        kit_instance.add_use(s, ajournal.start, source=ajournal, owner=self.owner_out)
                        log.debug(f'Added usage for {kit_instance}')
            else:
                log.debug(f'No kit defined for this activity ({time})')
