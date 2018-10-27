
import datetime as dt
from re import search

from urwid import Text, Pile, Columns, Divider

from . import Displayer
from .heart_rate import build_zones
from ..calculate.activity import ActivityStatistics
from ..names import ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MEDIAN_KM_TIME_ANY, MAX_MED_HR_OVER_M_ANY
from ...lib.date import format_seconds, local_date_to_time
from ...lib.utils import label
from ...squeal.tables.activity import ActivityGroup, ActivityJournal
from ...squeal.tables.source import Source
from ...squeal.tables.statistic import StatisticJournal, StatisticName
from ...uweird.tui.decorators import Indent

HRZ_WIDTH = 30


class ActivityDiary(Displayer):

    def build(self, s, f, date):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        for activity_group in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            for journal in s.query(ActivityJournal). \
                    filter(ActivityJournal.time >= start,
                           ActivityJournal.time < finish,
                           ActivityJournal.activity_group == activity_group). \
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
            sjournal = self._journal_at_time(s, ajournal.time, name, ActivityStatistics, ajournal.activity_group.id)
            body.append(Text([label('%s: ' % sjournal.statistic_name.name)] + self.__format_value(sjournal, date)))
        return body

    def __template(self, s, ajournal, template, title, re, date):
        body = [Text(title)]
        sjournals = s.query(StatisticJournal).join(StatisticName, Source). \
            filter(Source.time == ajournal.time,
                   StatisticName.name.like(template),
                   StatisticName.owner == ActivityStatistics,
                   StatisticName.constraint == ajournal.activity_group.id).order_by(StatisticName.name).all()
        # extract
        for sjournal in sorted(sjournals,
                               # order by integer embedded in name
                               key=lambda sjournal: int(search(r'(\d+)', sjournal.statistic_name.name).group(1))):
            body.append(Text([label(search(re, sjournal.statistic_name.name).group(1) + ': ')] +
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
