import datetime as dt
from logging import getLogger

from sqlalchemy import desc, asc

from . import MultiProcCalculator, ActivityJournalCalculatorMixin
from .activity import ActivityCalculator
from ..names import ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MAX_MEAN_PE_M_ANY, FITNESS_D_ANY, _delta, TOTAL_CLIMB, \
    CLIMB_DISTANCE, CLIMB_ELEVATION, PERCENT_IN_Z_ANY, TIME_IN_Z_ANY, MAX_MED_HR_M_ANY
from ...lib import local_time_to_time
from ...lib.log import log_current_exception
from ...sql import ActivityJournal, Timestamp, StatisticName, StatisticJournal, Achievement
from ...sql.tables.statistic import STATISTIC_JOURNAL_CLASSES
from ...sql.utils import add

log = getLogger(__name__)


class AchievementCalculator(ActivityJournalCalculatorMixin, MultiProcCalculator):

    def _delete(self, s):
        start, finish = self._start_finish(type=local_time_to_time)
        s.commit()   # so that we don't have any risk of having something in the session that can be deleted
        journal_ids = s.query(ActivityJournal.id)
        if start is not None:
            journal_ids = journal_ids.filter(ActivityJournal.finish > start)
        if finish is not None:
            journal_ids = journal_ids.filter(ActivityJournal.start < finish)
        q = s.query(Achievement).filter(Achievement.activity_journal_id.in_(journal_ids))
        n = q.count()
        log.debug(f'Deleting {n} achievements')
        q.delete(synchronize_session=False)
        Timestamp.clear_keys(s, journal_ids, owner=self.owner_out)

    def _startup(self, s):
        self._table = self._build_table(s)

    def _build_table(self, s):
        table = []
        self._append_like(table, s, 'longest', ACTIVE_DISTANCE, ActivityCalculator)
        self._append_like(table, s, 'longest', ACTIVE_TIME, ActivityCalculator)
        self._append_like(table, s, 'fastest', ACTIVE_SPEED, ActivityCalculator)
        self._append_like(table, s, 'highest', MAX_MEAN_PE_M_ANY, ActivityCalculator)
        self._append_like(table, s, 'highest', _delta(FITNESS_D_ANY), ActivityCalculator)
        self._append_like(table, s, 'highest', TOTAL_CLIMB, ActivityCalculator)
        self._append_like(table, s, 'highest', CLIMB_ELEVATION, ActivityCalculator)
        self._append_like(table, s, 'highest', CLIMB_DISTANCE, ActivityCalculator)
        self._append_like(table, s, 'highest', PERCENT_IN_Z_ANY, ActivityCalculator)
        self._append_like(table, s, 'longest', TIME_IN_Z_ANY, ActivityCalculator)
        self._append_like(table, s, 'highest', MAX_MED_HR_M_ANY, ActivityCalculator)
        return table

    def _append_like(self, table, s, superlative, pattern, owner):
        for statistic_name in s.query(StatisticName). \
                filter(StatisticName.name.like(pattern),
                       StatisticName.owner == owner):
            table.append((superlative, statistic_name))

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
        self._check_all(s, activity_journal)

    def _check_all(self, s, activity_journal):
        for (superlative, statistic_name) in self._table:
            for (days, period) in [(50 * 365, 'all time'), (365, 'the last year'),
                                   (30, 'the last 30 days'), (7, 'the last week')]:
                rank, achievement = self._check(s, activity_journal, superlative, statistic_name, days, period)
                if achievement:
                    log.debug(f'{achievement}')
                    add(s, Achievement(text=achievement, level=rank+1, activity_journal=activity_journal))
                    break  # if month, also week

    def _check(self, s, activity_journal, superlative, statistic_name, days, period):
        try:
            less_is_better = 'min' in statistic_name.summaries
            order = asc if less_is_better else desc
            journal_class = STATISTIC_JOURNAL_CLASSES[statistic_name.statistic_journal_type]
            best_values = s.query(journal_class.value). \
                filter(StatisticJournal.statistic_name == statistic_name,
                       StatisticJournal.time >= activity_journal.start - dt.timedelta(days=days),
                       StatisticJournal.time < activity_journal.finish). \
                order_by(order(journal_class.value)). \
                limit(4).all()  # 4 so we know something worse
            best_values = [values[0] for values in best_values]
            current_value = s.query(journal_class.value). \
                filter(StatisticJournal.statistic_name == statistic_name,
                       StatisticJournal.time >= activity_journal.start,
                       StatisticJournal.time < activity_journal.finish).scalar()
            for rank, adjective in enumerate(('%s', 'second %s', 'third %s')):
                description = adjective % superlative
                # +1 below so we don't give prizes for last
                if len(best_values) > rank+1 and current_value == best_values[rank]:
                    achievement = f'{description} {statistic_name.name.lower()} in {period}'
                    achievement = achievement[0].upper() + achievement[1:]
                    return rank, achievement
        except Exception as e:
            log.warning(f'No achievement for {statistic_name}: {e}')
            log_current_exception()
        return 0, None
