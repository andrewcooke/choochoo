from logging import getLogger

from .utils import ActivityJournalCalculatorMixin, ProcessCalculator
from ...common.date import local_time_to_time
from ...sql import Timestamp

log = getLogger(__name__)


class FindSectorCalculator(ActivityJournalCalculatorMixin, ProcessCalculator):
    '''
    Run through new activity journals, find any sectors that match, and populate the SectorJournal.
    '''

    def _run_one(self, missed):
        start = local_time_to_time(missed)
        with self._config.db.session_context() as s:
            ajournal = self._get_source(s, start)
            with Timestamp(owner=self.owner_out, source=ajournal).on_success(s):
                if ajournal.route_edt:
                    pass
