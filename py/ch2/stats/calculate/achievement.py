from logging import getLogger

from . import MultiProcCalculator, ActivityJournalCalculatorMixin
from ...lib.log import log_current_exception
from ...sql import ActivityJournal, Timestamp

log = getLogger(__name__)


class AchievementCalculator(ActivityJournalCalculatorMixin, MultiProcCalculator):

    def _run_one(self, s, time_or_date):
        activity_journal = s.query(ActivityJournal).filter(ActivityJournal.start == time_or_date).one()
        with Timestamp(owner=self.owner_out, source=activity_journal).on_success(s):
            try:
                self._calculate_stats(s, activity_journal)
            except Exception as e:
                log.warning(f'No statistics on {time_or_date}: {e}')
                log_current_exception()

    def _calculate_stats(self, s, activity_journal):
        log.debug(f'Calculate for {activity_journal} on {activity_journal.start}')

