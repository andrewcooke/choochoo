
from logging import getLogger
from re import search

from urwid import Text, Pile, Columns, Divider

from . import JournalDiary
from .heart_rate import build_zones
from ..calculate.activity import ActivityCalculator
from ..calculate.power import PowerCalculator
from ..names import ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MED_KM_TIME_ANY, MAX_MED_HR_M_ANY, CLIMB_ELEVATION, \
    CLIMB_DISTANCE, CLIMB_GRADIENT, CLIMB_TIME, TOTAL_CLIMB, MIN_KM_TIME_ANY, CALORIE_ESTIMATE, \
    ENERGY_ESTIMATE, MEAN_POWER_ESTIMATE, MAX_MEAN_PE_M_ANY
from ...data.climb import climbs_for_activity
from ...lib.date import format_seconds, time_to_local_time, to_time, HMS
from ...lib.utils import label
from ...squeal.tables.statistic import StatisticJournal, StatisticName
from ...uweird.fields.summary import summary_columns
from ...uweird.tui.decorators import Indent

log = getLogger(__name__)
HRZ_WIDTH = 30


class ActivityDiary(JournalDiary):

    def _journal_date(self, s, f, ajournal, date):
        zones = build_zones(s, ajournal, HRZ_WIDTH)
        active_date = self.__active_date(s, ajournal, date)
        climbs = self.__climbs(s, ajournal, date)
        details = Pile(([] if climbs else [Divider()]) + active_date + climbs)
        yield Pile([
            Text(ajournal.name),
            Indent(Columns([details, (HRZ_WIDTH + 2, zones)])),
            Divider(),
            Indent(Columns([Pile(self.__template(s, ajournal, MIN_KM_TIME_ANY, 'Min Time', r'(\d+km)', date) +
                                 self.__template(s, ajournal, MED_KM_TIME_ANY, 'Med Time', r'(\d+km)', date)),
                            Pile(self.__template(s, ajournal, MAX_MED_HR_M_ANY, 'Max Med Heart Rate', r'(\d+m)', date) +
                                 self.__template(s, ajournal, MAX_MEAN_PE_M_ANY, 'Max Mean Power Estimate', r'(\d+m)', date))]))
        ])

    def __active_date(self, s, ajournal, date):
        body = []
        body.append(Text('%s - %s  (%s)' % (time_to_local_time(to_time(ajournal.start)),
                                            time_to_local_time(to_time(ajournal.finish), fmt=HMS),
                                            format_seconds((ajournal.finish - ajournal.start).seconds))))
        for name in (ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MEAN_POWER_ESTIMATE):
            sjournal = StatisticJournal.at(s, ajournal.start, name, ActivityCalculator, ajournal.activity_group)
            if sjournal:
                body.append(Text([label('%s: ' % sjournal.statistic_name.name)] + self.__format_value(sjournal, date)))
        for name in (ENERGY_ESTIMATE, CALORIE_ESTIMATE):
            sjournal = StatisticJournal.at(s, ajournal.start, name, PowerCalculator, ajournal.activity_group)
            if sjournal:
                body.append(Text([label('%s: ' % sjournal.statistic_name.name)] + self.__format_value(sjournal, date)))
        return body

    def __climbs(self, s, ajournal, date):
        total, climbs = climbs_for_activity(s, ajournal)
        if total:
            body = [Text(['Climbs ', label('Total: '), '%dm ' % total.value, *total.measures_as_text(date)])]
            for climb in climbs:
                body.append(Text(['%3sm/%.1fkm (%d%%)' %
                                  (int(climb[CLIMB_ELEVATION].value), # display int() with %s to get space padding
                                   climb[CLIMB_DISTANCE].value / 1000, climb[CLIMB_GRADIENT].value),
                                  label(' in '),
                                  format_seconds(climb[CLIMB_TIME].value),
                                  ' ',
                                  *climb[CLIMB_ELEVATION].measures_as_text(date),
                                  ]))
            return body
        else:
            return []

    def __template(self, s, ajournal, template, title, re, date):
        body = [Text(title)]
        sjournals = s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticJournal.time == ajournal.start,
                   StatisticName.name.like(template),
                   StatisticName.owner == ActivityCalculator,
                   StatisticName.constraint == ajournal.activity_group).order_by(StatisticName.name).all()
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

    def _display_schedule(self, s, f, date, schedule=None):
        columns = list(self.__schedule_fields(s, f, date, schedule))
        if columns:
            yield Pile([Text('Activities'),
                        Indent(Pile(columns))])

    def __schedule_fields(self, s, f, date, schedule):
        names = list(self.__names(s, ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED,
                                  TOTAL_CLIMB, CLIMB_ELEVATION, CLIMB_DISTANCE, CLIMB_GRADIENT, CLIMB_TIME))
        yield from summary_columns(log, s, f, date, schedule, names)
        names = self.__sort_names(self.__names_like(s, MIN_KM_TIME_ANY))
        yield from summary_columns(log, s, f, date, schedule, names)
        names = self.__sort_names(self.__names_like(s, MED_KM_TIME_ANY))
        yield from summary_columns(log, s, f, date, schedule, names)
        names = self.__sort_names(self.__names_like(s, MAX_MED_HR_M_ANY))
        yield from summary_columns(log, s, f, date, schedule, names)

    def __names(self, s, *names):
        for name in names:
            yield s.query(StatisticName). \
                filter(StatisticName.name == name,
                       StatisticName.owner == ActivityCalculator).one()

    def __names_like(self, s, name):
        return s.query(StatisticName). \
            filter(StatisticName.name.like(name),
                   StatisticName.owner == ACTIVE_DISTANCE).all()
