
from re import search

from urwid import Text, Pile, Columns, Divider

from ch2.lib.utils import label
from ch2.squeal.tables.source import Source
from ch2.stoats.calculate.activity import ActivityStatistics
from .heart_rate import build_zones
from ..names import ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MEDIAN_KM_TIME_ANY, MAX_MED_HR_OVER_M_ANY
from ...lib.date import to_date, format_seconds, DAY, add_date
from ...squeal.tables.activity import Activity, ActivityJournal
from ...squeal.tables.statistic import StatisticJournal, Statistic
from ...uweird.tui.decorators import Indent

HRZ_WIDTH = 30


class ActivityDiary:

    def __init__(self, log):
        self._log = log

    def build(self, s, f, date):
        start = to_date(date)
        finish = add_date(start, (1, DAY))
        for activity in s.query(Activity).order_by(Activity.sort).all():
            for journal in s.query(ActivityJournal). \
                    filter(ActivityJournal.time >= start,
                           ActivityJournal.time < finish,
                           ActivityJournal.activity == activity). \
                    order_by(ActivityJournal.time).all():
                yield self.__journal_data(s, journal, date)

    def __journal_data(self, s, ajournal, date):
        zones = build_zones(s, ajournal, HRZ_WIDTH)
        details = Pile(self.__active_data(s, ajournal, date))
        return Pile([
            Text(ajournal.name),
            Indent(Columns([details, (HRZ_WIDTH + 2, zones)])),
            Divider(),
            Indent(Columns([Pile(self.__template(s, ajournal, MEDIAN_KM_TIME_ANY,
                                                 'Median Time', r'(\d+km)', date)),
                            Pile(self.__template(s, ajournal, MAX_MED_HR_OVER_M_ANY,
                                                 'Max Med HR', r'(\d+m)', date))]))
        ])

    def __active_data(self, s, ajournal, date):
        body = [Divider()]
        body.append(Text('%s - %s  (%s)' % (ajournal.time.strftime('%H:%M:%S'), ajournal.finish.strftime('%H:%M:%S'),
                                            format_seconds((ajournal.finish - ajournal.time).seconds))))
        for name in (ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED):
            sjournal = StatisticJournal.get(s, name, ajournal.time, ActivityStatistics, ajournal.activity.id)
            body.append(Text([label('%s: ' % sjournal.statistic.name)] + self.__format_value(sjournal, date)))
        return body

    def __template(self, s, ajournal, template, title, re, date):
        body = [Text(title)]
        sjournals = s.query(StatisticJournal).join(Statistic, Source). \
            filter(Source.time == ajournal.time,
                   Statistic.name.like(template),
                   Statistic.owner == ActivityStatistics,
                   Statistic.constraint == ajournal.activity.id).order_by(Statistic.name).all()
        # extract
        for sjournal in sorted(sjournals,
                               # order by integer embedded in name
                               key=lambda sjournal: int(search(r'(\d+)', sjournal.statistic.name).group(1))):
            body.append(Text([label(search(re, sjournal.statistic.name).group(1) + ': ')] +
                             self.__format_value(sjournal, date)))
        return body

    def __format_value(self, sjournal, date):
        words, first = ['%s ' % sjournal.formatted()], True
        for measure in sorted(sjournal.measures,
                              key=lambda measure: measure.source.schedule.frame_length_in_days(date)):
            if not first:
                words += [',']
            first = False
            quintile = 1 + min(4, measure.percentile / 20)
            words += [('quintile-%d' % quintile, '%d%%' % int(measure.percentile))]
            if measure.rank < 5:
                words += [':', ('rank-%d' % measure.rank, '%d' % measure.rank)]
            words += ['/' + measure.source.schedule.describe(compact=True)]
        return words
