
from urwid import Text, Pile

from ...lib.date import to_date, add_duration
from ...squeal.tables.activity import Activity, ActivityJournal


class ActivityDiary:

    def __init__(self, log):
        self._log = log

    def build(self, s, f, date):
        start = to_date(date)
        finish = add_duration(start, (1, 'd'))
        for activity in s.query(Activity).order_by(Activity.sort).all():
            for journal in s.query(ActivityJournal). \
                    filter(ActivityJournal.time >= start,
                           ActivityJournal.time < finish,
                           ActivityJournal.activity == activity). \
                    order_by(ActivityJournal.time).all():
                yield self.__journal(s, f, journal)

    def __journal(self, s, f, journal):
        body = [Text(journal.name)]
        return Pile(body)
