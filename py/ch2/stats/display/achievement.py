
from logging import getLogger
import datetime as dt

from sqlalchemy import desc

from ..display import Displayer, ActivityJournalDelegate
from ...diary.model import optional_text, text
from ...lib import local_date_to_time
from ...sql import ActivityGroup, ActivityJournal, Achievement

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

    def read_schedule(self, s, date, schedule):
        # todo?
        return
        yield


class AchievementDiary(Displayer):

    @optional_text('Achievements')
    def _read_date(self, s, date):
        journals = list(self._journals_at_date(s, date))
        for journal in journals:
            achievements = list(self._achievements_for_journal(s, journal))
            if not achievements: achievements = [text('Get out and try harder!')]
            if len(journals) > 1:
                achievements = [text('journal name')] + achievements
                yield achievements
            else:
                yield from achievements

    def _journals_at_date(self, s, date):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        for activity_group in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            for ajournal in s.query(ActivityJournal). \
                    filter(ActivityJournal.finish >= start,
                           ActivityJournal.start < finish,
                           ActivityJournal.activity_group == activity_group). \
                    order_by(ActivityJournal.start).all():
                yield ajournal

    def _achievements_for_journal(self, s, journal):
        for achievement in s.query(Achievement). \
                filter(Achievement.activity_journal == journal). \
                order_by(desc(Achievement.sort)).limit(5).all():   # limit 5 for compact display
            yield text(achievement.text)

    def _read_schedule(self, s, date, schedule):
        return
        yield
