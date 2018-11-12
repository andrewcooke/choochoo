
import datetime as dt
from re import search

from urwid import Text, Pile, Columns, Divider

from . import Displayer
from .heart_rate import build_zones
from ..calculate.activity import ActivityStatistics
from ..names import ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MEDIAN_KM_TIME_ANY, MAX_MED_HR_M_ANY
from ...lib.date import format_seconds, local_date_to_time
from ...lib.utils import label
from ...squeal.tables.activity import ActivityGroup, ActivityJournal
from ...squeal.tables.source import Source
from ...squeal.tables.statistic import StatisticJournal, StatisticName
from ch2.uweird.fields.summary import summary_columns
from ...uweird.tui.decorators import Indent

HRZ_WIDTH = 30


class ActivityDiary(Displayer):

    def build(self, s, f, date, schedule=None):
        if schedule:
            yield from self.__build_schedule(s, f, date, schedule)
        else:
            yield from self.__build_date(s, f, date)

    def __build_date(self, s, f, date):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        for activity_group in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            for journal in s.query(ActivityJournal). \
                    filter(ActivityJournal.finish >= start,
                           ActivityJournal.start < finish,
                           ActivityJournal.activity_group == activity_group). \
                    order_by(ActivityJournal.start).all():
                yield self.__journal_date(s, journal, date)

    def __journal_date(self, s, ajournal, date):
        zones = build_zones(s, ajournal, HRZ_WIDTH)
        details = Pile(self.__active_date(s, ajournal, date))
        return Pile([
            Text(ajournal.name),
            Indent(Columns([details, (HRZ_WIDTH + 2, zones)])),
            Divider(),
            Indent(Columns([Pile(self.__template(s, ajournal, MEDIAN_KM_TIME_ANY,
                                                 'Median Time', r'(\d+km)', date)),
                            Pile(self.__template(s, ajournal, MAX_MED_HR_M_ANY,
                                                 'Max Med HR', r'(\d+m)', date))]))
        ])

    def __active_date(self, s, ajournal, date):
        body = [Divider()]
        body.append(Text('%s - %s  (%s)' % (ajournal.start.strftime('%H:%M:%S'), ajournal.finish.strftime('%H:%M:%S'),
                                            format_seconds((ajournal.finish - ajournal.start).seconds))))
        for name in (ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED):
            sjournal = StatisticJournal.at(s, ajournal.start, name, ActivityStatistics, ajournal.activity_group)
            body.append(Text([label('%s: ' % sjournal.statistic_name.name)] + self.__format_value(sjournal, date)))
        return body

    def __template(self, s, ajournal, template, title, re, date):
        body = [Text(title)]
        sjournals = s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticJournal.time == ajournal.start,
                   StatisticName.name.like(template),
                   StatisticName.owner == ActivityStatistics,
                   StatisticName.constraint == ajournal.activity_group.id).order_by(StatisticName.name).all()
        # extract
        for sjournal in self.__sort_journals(sjournals):
            body.append(Text([label(search(re, sjournal.statistic_name.name).group(1) + ': ')] +
                             self.__format_value(sjournal, date)))
        return body

    def __sort_journals(self, sjournals):
        return sorted(sjournals,
                      # order by integer embedded in name
                      key=lambda sjournal: int(search(r'(\d+)', sjournal.statistic_name.name).group(1)))

    def __sort_names(self, statistic_names):
        return sorted(statistic_names,
                      # order by integer embedded in name
                      key=lambda statistic_name: int(search(r'(\d+)', statistic_name.name).group(1)))

    def __format_value(self, sjournal, date):
        return ['%s ' % sjournal.formatted()] + sjournal.measures_as_text(date)

    def __build_schedule(self, s, f, date, schedule):
        columns = list(self.__schedule_fields(s, f, date, schedule))
        if columns:
            yield Pile([Text('Activities'),
                        Indent(Pile(columns))])

    def __schedule_fields(self, s, f, date, schedule):
        names = list(self.__names(s, ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED))
        yield from summary_columns(self._log, s, f, date, schedule, names)
        names = self.__sort_names(self.__names_like(s, MEDIAN_KM_TIME_ANY))
        yield from summary_columns(self._log, s, f, date, schedule, names)
        names = self.__sort_names(self.__names_like(s, MAX_MED_HR_M_ANY))
        yield from summary_columns(self._log, s, f, date, schedule, names)

    def __names(self, s, *names):
        for name in names:
            yield s.query(StatisticName). \
                filter(StatisticName.name == name,
                       StatisticName.owner == ActivityStatistics).one()

    def __names_like(self, s, name):
        return s.query(StatisticName). \
                filter(StatisticName.name.like(name),
                       StatisticName.owner == ActivityStatistics).all()
