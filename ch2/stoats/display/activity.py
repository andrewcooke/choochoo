
from urwid import Text, Pile, Columns

from .heart_rate import build_zones
from ..names import ACTIVE_DISTANCE, ACTIVE_TIME
from ...lib.date import to_date, add_duration, format_seconds
from ...squeal.tables.activity import Activity, ActivityJournal
from ...squeal.tables.statistic import StatisticJournal, Statistic
from ...uweird.tui.decorators import Indent

HRZ_WIDTH = 30


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
                yield self.__journal(s, journal)

    def __journal(self, s, journal):
        zones = build_zones(s, journal, HRZ_WIDTH)
        details = Pile(self.__details(s, journal))
        return Pile([
            Text(journal.name),
            Indent(Columns([details, (HRZ_WIDTH + 2, zones)]))
        ])

    def __details(self, s, journal):
        body = []
        body.append(Text('%s - %s  (%s)' % (journal.time.strftime('%H:%M:%S'), journal.finish.strftime('%H:%M:%S'),
                                            format_seconds((journal.finish - journal.time).seconds))))
        for name in (ACTIVE_DISTANCE, ACTIVE_TIME):
            statistic = s.query(StatisticJournal).join(Statistic). \
                filter(StatisticJournal.source == journal,
                       Statistic.name == name).one()
            body.append(self.__format(statistic))
        return body

    def __format(self, journal):
        words, first = ['%s: %s' % (journal.statistic.name, journal.formatted())], True
        for measure in journal.measures:
            if not first:
                words += [',']
            if measure.rank < 5:
                words += [' ', ('rank-%d' % measure.rank, '%d' % measure.rank),
                          '/' + measure.source.schedule.describe(compact=True)]
            first = False
        return Text(words)
