
from logging import getLogger

from sqlalchemy import desc

from ..utils import ActivityJournalDelegate
from ....diary.model import optional_text, text
from ....sql import Achievement

log = getLogger(__name__)


class AchievementDelegate(ActivityJournalDelegate):

    @optional_text('Achievements')
    def read_journal_date(self, s, ajournal, date):
        achievements = list(self._achievements_for_journal(s, ajournal))
        if not achievements: achievements = [text('Get out and try harder!')]
        yield from achievements

    def _achievements_for_journal(self, s, ajournal):
        for achievement in s.query(Achievement). \
                filter(Achievement.activity_journal == ajournal). \
                order_by(desc(Achievement.sort)).limit(5).all():   # limit 5 for compact display
            yield text(achievement.text)

    def read_interval(self, s, interval):
        # todo?
        return
        yield


