import datetime as dt
from logging import getLogger
from re import compile

from sqlalchemy import desc, asc

from . import MultiProcCalculator, ActivityJournalCalculatorMixin
from .activity import ActivityCalculator
from ..names import ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MAX_MEAN_PE_M_ANY, FITNESS_D_ANY, _delta, TOTAL_CLIMB, \
    CLIMB_DISTANCE, CLIMB_ELEVATION, MAX_MED_HR_M_ANY, MIN_KM_TIME_ANY
from ...lib import local_time_to_time
from ...lib.log import log_current_exception
from ...sql import ActivityJournal, Timestamp, StatisticName, StatisticJournal, Achievement, ActivityGroup
from ...sql.tables.statistic import STATISTIC_JOURNAL_CLASSES, StatisticJournalFloat
from ...sql.types import short_cls
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
        self._append_like(table, s, 'fastest', 15, MIN_KM_TIME_ANY, ActivityCalculator)
        self._append_like(table, s, 'longest', 10, ACTIVE_DISTANCE, ActivityCalculator)
        self._append_like(table, s, 'longest', 10, ACTIVE_TIME, ActivityCalculator)
        self._append_like(table, s, 'fastest', 10, ACTIVE_SPEED, ActivityCalculator)
        self._append_like(table, s, 'highest', 3, MAX_MEAN_PE_M_ANY, ActivityCalculator)
        self._append_like(table, s, 'highest', 10, _delta(FITNESS_D_ANY), ActivityCalculator)
        self._append_like(table, s, 'highest', 10, TOTAL_CLIMB, ActivityCalculator)
        self._append_like(table, s, 'highest', 5, CLIMB_ELEVATION, ActivityCalculator)
        self._append_like(table, s, 'highest', 5, CLIMB_DISTANCE, ActivityCalculator)
        self._append_like(table, s, 'highest', 3, MAX_MED_HR_M_ANY, ActivityCalculator)
        return table

    def _append_like(self, table, s, superlative, score, pattern, owner):
        for statistic_name in s.query(StatisticName). \
                filter(StatisticName.name.like(pattern),
                       StatisticName.owner == owner):
            table.append((superlative, statistic_name, score))

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

    def _build_query(self, s, activity_journal, statistic_name, days=0):
        less_is_better = 'min' in statistic_name.summaries
        order = asc if less_is_better else desc
        journal_class = STATISTIC_JOURNAL_CLASSES[statistic_name.statistic_journal_type]
        q = s.query(journal_class.value). \
            filter(StatisticJournal.statistic_name == statistic_name,
                   StatisticJournal.time >= activity_journal.start - dt.timedelta(days=days),
                   StatisticJournal.time < activity_journal.finish)
        if journal_class == StatisticJournalFloat:
            q = q.filter(journal_class.value != 0.0)
        q = q.order_by(order(journal_class.value))
        return q

    def _check(self, s, activity_journal, superlative, statistic_name, days, period):
        try:
            group = self.parse_group(statistic_name)
            # 4 so we know something worse
            best_values = self._build_query(s, activity_journal, statistic_name, days).limit(4).all()
            best_values = [x[0] for x in best_values]
            current_value = self._build_query(s, activity_journal, statistic_name).limit(1).scalar()
            for rank, adjective in enumerate(('%s', '2nd %s', '3rd %s')):
                description = adjective % superlative
                # +1 below so we don't give prizes for last
                if len(best_values) > rank+1 and current_value == best_values[rank]:
                    achievement = f'{description} {lower(statistic_name.name)} {period} (for {group})'
                    achievement = achievement[0].upper() + achievement[1:]
                    return rank, achievement, group == 'all'
        except Exception as e:
            log.warning(f'No achievement for {statistic_name}: {e}')
            log_current_exception()
        return 0, None, False

    @staticmethod
    def parse_group(statistic_name):
        # activity group is encoded into the statistic name constraint
        constraint = statistic_name.constraint
        if constraint.startswith(short_cls(ActivityGroup)):
            return lower(constraint.split('"')[1])
        else:
            return 'all'


def lower(text):
    def l(word):
        if compile(r'^[A-Z][a-z]+$').match(word):
            word = word[0].lower() + word[1:]
        return word
    return ' '.join(l(word) for word in text.split(' '))
