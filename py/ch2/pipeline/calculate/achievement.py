import datetime as dt
from logging import getLogger
from re import compile

from sqlalchemy import desc, asc

from .utils import ProcessCalculator, ActivityJournalCalculatorMixin
from ..pipeline import OwnerInMixin
from ...lib import local_time_to_time
from ...common.log import log_current_exception
from ...names import N
from ...sql import ActivityJournal, Timestamp, StatisticName, StatisticJournal, Achievement, ActivityGroup, Source
from ...sql.tables.statistic import STATISTIC_JOURNAL_CLASSES, StatisticJournalFloat
from ...sql.utils import add

log = getLogger(__name__)


class AchievementCalculator(OwnerInMixin, ActivityJournalCalculatorMixin, ProcessCalculator):

    def _startup(self, s):
        super()._startup(s)
        table = []
        self._append_like(table, s, 'fastest', 15, N.MIN_KM_TIME_ANY, self.owner_in)
        self._append_like(table, s, 'longest', 10, N.ACTIVE_DISTANCE, self.owner_in)
        self._append_like(table, s, 'longest', 10, N.ACTIVE_TIME, self.owner_in)
        self._append_like(table, s, 'fastest', 10, N.ACTIVE_SPEED, self.owner_in)
        self._append_like(table, s, 'highest', 3, N.MAX_MEAN_PE_M_ANY, self.owner_in)
        self._append_like(table, s, 'highest', 10, N._delta(N.FITNESS_ANY), self.owner_in)
        self._append_like(table, s, 'highest', 10, N.TOTAL_CLIMB, self.owner_in)
        self._append_like(table, s, 'highest', 5, N.CLIMB_ELEVATION, self.owner_in)
        self._append_like(table, s, 'highest', 5, N.CLIMB_DISTANCE, self.owner_in)
        self._append_like(table, s, 'highest', 3, N.MAX_MED_HR_M_ANY, self.owner_in)
        self._table = table

    def _append_like(self, table, s, superlative, score, pattern, owner):
        found = 0
        for statistic_name in s.query(StatisticName). \
                filter(StatisticName.name.like(pattern),
                       StatisticName.owner == owner):
            found += 1
            table.append((superlative, statistic_name, score))
        if found:
            log.debug(f'Matched {found} statistics for {pattern} ({owner})')
        else:
            log.warning(f'No matches for {pattern} ({owner})')

    def _run_one(self, missed):
        start = local_time_to_time(missed)
        with self._config.db.session_context() as s:
            activity_journal = s.query(ActivityJournal).filter(ActivityJournal.start == start).one()
            with Timestamp(owner=self.owner_out, source=activity_journal).on_success(s):
                try:
                    self._calculate_stats(s, activity_journal)
                except Exception as e:
                    log.error(f'No statistics on {missed}: {e}')
                    log_current_exception()

    def _calculate_stats(self, s, activity_journal):
        log.debug(f'Calculate for {activity_journal} on {activity_journal.start}')
        self._check_all(s, activity_journal)

    def _check_all(self, s, activity_journal):
        for (superlative, statistic_name, statistic_score) in self._table:
            # going down to a week gets way too many
            for (days, period, period_score) in [(50 * 365, 'of all time', 10),
                                                 (365, 'in a year', 5),
                                                 (30, 'in 30 days', 1)]:
                rank, achievement, all = self._check(s, activity_journal, superlative, statistic_name, days, period)
                if achievement:
                    score = statistic_score + period_score - rank + (4 if all else 0)
                    log.debug(f'{achievement}/{score}')
                    add(s, Achievement(text=achievement, sort=score, activity_journal=activity_journal))
                    break  # if month, also week

    def _query_values(self, s, activity_journal, activity_group, statistic_name, days=0):
        less_is_better = 'min' in statistic_name.summaries
        order = asc if less_is_better else desc
        journal_class = STATISTIC_JOURNAL_CLASSES[statistic_name.statistic_journal_type]
        q = s.query(journal_class.value).join(Source). \
            filter(StatisticJournal.statistic_name == statistic_name,
                   Source.activity_group == activity_group,
                   StatisticJournal.time >= activity_journal.start - dt.timedelta(days=days),
                   StatisticJournal.time < activity_journal.finish)
        if journal_class == StatisticJournalFloat:
            q = q.filter(journal_class.value != 0.0)
        q = q.order_by(order(journal_class.value))
        return q

    def _query_group(self, s, activity_journal, statistic_name):
        return s.query(ActivityGroup). \
            join(ActivityJournal). \
            join(StatisticJournal, StatisticJournal.source_id == ActivityJournal.id). \
            join(StatisticName). \
            filter(ActivityJournal.id == activity_journal.id,
                   StatisticName.id == statistic_name.id).one_or_none()

    def _check(self, s, activity_journal, superlative, statistic_name, days, period):
        try:
            activity_group = self._query_group(s, activity_journal, statistic_name)
            # 4 so we know something worse
            best_values = self._query_values(s, activity_journal, activity_group, statistic_name, days). \
                limit(4).all()
            best_values = [x[0] for x in best_values]
            current_value = self._query_values(s, activity_journal, activity_group, statistic_name).limit(1).scalar()
            for rank, adjective in enumerate(('%s', '2nd %s', '3rd %s')):
                description = adjective % superlative
                # +1 below so we don't give prizes for last
                if len(best_values) > rank+1 and current_value == best_values[rank]:
                    group = activity_group.name if activity_group else 'all'
                    achievement = f'{description} {lower(statistic_name.title)} {period} (for {group})'
                    achievement = achievement[0].upper() + achievement[1:]
                    return rank, achievement, group == 'all'
        except Exception as e:
            log.warning(f'No achievement for {statistic_name}: {e}')
            log_current_exception()
        return 0, None, False


def lower(text):
    def l(word):
        if compile(r'^[A-Z][a-z]+$').match(word):
            word = word[0].lower() + word[1:]
        return word
    return ' '.join(l(word) for word in text.split(' '))
