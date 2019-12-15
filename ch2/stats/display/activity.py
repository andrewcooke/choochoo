
from logging import getLogger
from re import search

from urwid import Text, Pile, Columns, Divider

from . import JournalDiary
from .heart_rate import build_zones, read_zones
from ..calculate.activity import ActivityCalculator
from ..calculate.power import PowerCalculator
from ..names import ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MED_KM_TIME_ANY, MAX_MED_HR_M_ANY, CLIMB_ELEVATION, \
    CLIMB_DISTANCE, CLIMB_GRADIENT, CLIMB_TIME, TOTAL_CLIMB, MIN_KM_TIME_ANY, CALORIE_ESTIMATE, \
    ENERGY_ESTIMATE, MEAN_POWER_ESTIMATE, MAX_MEAN_PE_M_ANY, FITNESS_D_ANY, FATIGUE_D_ANY, _d, M, KM, S
from ..read.segment import SegmentReader
from ...data.climb import climbs_for_activity
from ...diary.model import text, value
from ...lib.date import format_seconds, time_to_local_time, to_time, HMS, local_date_to_time
from ...lib.utils import label
from ...sql import ActivityGroup, ActivityJournal, StatisticJournal, StatisticName
from ...urwid.fields.summary import summary_columns
from ...urwid.tui.decorators import Indent

log = getLogger(__name__)
HRZ_WIDTH = 30


class ActivityDiary(JournalDiary):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    def _journal_date(self, s, f, ajournal, date):
        zones = build_zones(s, ajournal, HRZ_WIDTH)
        active_date = self.__active_data(s, ajournal, date)
        climbs = self.__climbs(s, ajournal, date)
        details = Pile(([] if climbs else [Divider()]) + active_date + climbs)
        yield Pile([
            Text(self.__title(s, ajournal)),
            Indent(Columns([details, (HRZ_WIDTH + 2, zones)])),
            Divider(),
            Indent(Columns([Pile(self.__template(s, ajournal, MIN_KM_TIME_ANY, 'Min Time', r'(\d+km)', date) +
                                 self.__template(s, ajournal, MED_KM_TIME_ANY, 'Med Time', r'(\d+km)', date)),
                            Pile(self.__template(s, ajournal, MAX_MED_HR_M_ANY, 'Max Med Heart Rate', r'(\d+m)', date) +
                                 self.__template(s, ajournal, MAX_MEAN_PE_M_ANY, 'Max Mean Power Estimate', r'(\d+m)', date))]))
        ])

    def _read_journal_date(self, s, ajournal, date):
        yield text(self.__title(s, ajournal))
        yield list(self.__read_details(s, ajournal, date))

    def __read_details(self, s, ajournal, date):
        zones = list(read_zones(s, ajournal))
        if zones: yield [text('HR Zones (% time)'), zones]
        active_data = list(self.__read_active_data(s, ajournal, date))
        if active_data: yield [text('Activity Statistics'), active_data]
        climbs = list(self.__read_climbs(s, ajournal, date))
        if climbs: yield [text('Climbs'), climbs]

    def __title(self, s, ajournal):
        title = f'{ajournal.name} ({ajournal.activity_group.name}'
        kits = s.query(StatisticJournal). \
            join(StatisticName). \
            filter(StatisticJournal.source == ajournal,
                   StatisticName.name == 'kit',
                   StatisticName.owner == SegmentReader).all()
        if kits:
            title += '/' + ','.join(str(kit.value) for kit in kits)
        return title + ')'

    def __active_data(self, s, ajournal, date):
        body = []
        body.append(Text('%s - %s  (%s)' % (time_to_local_time(to_time(ajournal.start)),
                                            time_to_local_time(to_time(ajournal.finish), fmt=HMS),
                                            format_seconds((ajournal.finish - ajournal.start).seconds))))
        for name in (ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MEAN_POWER_ESTIMATE):
            sjournal = StatisticJournal.at(s, ajournal.start, name, ActivityCalculator, ajournal.activity_group)
            if sjournal:
                body.append(Text([label(f'{sjournal.statistic_name.name}: ')] + self.__format_value(sjournal, date)))
        for name in (_d(FITNESS_D_ANY), _d(FATIGUE_D_ANY)):
            for sjournal in StatisticJournal.at_like(s, ajournal.start, name, ActivityCalculator,
                                                     ajournal.activity_group):
                body.append(Text([label(f'{sjournal.statistic_name.name}: ')] + self.__format_value(sjournal, date)))
        for name in (ENERGY_ESTIMATE, CALORIE_ESTIMATE):
            sjournal = StatisticJournal.at(s, ajournal.start, name, PowerCalculator, ajournal.activity_group)
            if sjournal:
                body.append(Text([label(f'{sjournal.statistic_name.name}: ')] + self.__format_value(sjournal, date)))
        return body

    def __read_active_data(self, s, ajournal, date):
        yield text('%s - %s  (%s)' % (time_to_local_time(to_time(ajournal.start)),
                                      time_to_local_time(to_time(ajournal.finish), fmt=HMS),
                                      format_seconds((ajournal.finish - ajournal.start).seconds)))
        for name in (ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MEAN_POWER_ESTIMATE):
            sjournal = StatisticJournal.at(s, ajournal.start, name, ActivityCalculator, ajournal.activity_group)
            if sjournal:
                yield value(sjournal.statistic_name.name, sjournal.value,
                            units=sjournal.statistic_name.units,
                            measures=sjournal.measures_as_model(date))
        for name in (_d(FITNESS_D_ANY), _d(FATIGUE_D_ANY)):
            for sjournal in StatisticJournal.at_like(s, ajournal.start, name, ActivityCalculator,
                                                     ajournal.activity_group):
                yield value(sjournal.statistic_name.name, sjournal.value,
                            units=sjournal.statistic_name.units,
                            measures=sjournal.measures_as_model(date))
        for name in (ENERGY_ESTIMATE, CALORIE_ESTIMATE):
            sjournal = StatisticJournal.at(s, ajournal.start, name, PowerCalculator, ajournal.activity_group)
            if sjournal:
                yield value(sjournal.statistic_name.name, sjournal.value,
                            units=sjournal.statistic_name.units,
                            measures=sjournal.measures_as_model(date))

    def __climbs(self, s, ajournal, date):
        total, climbs = climbs_for_activity(s, ajournal)
        if total:
            body = [Text(['Climbs ', label('Total: '), f'{total.value:.0f}m ', *total.measures_as_text(date)])]
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

    def __read_climbs(self, s, ajournal, date):
        total, climbs = climbs_for_activity(s, ajournal)
        if total:
            yield value('Total Elevation', total.value, measures=total.measures_as_model(date), units=M)
            yield [[value('Elevation', climb[CLIMB_ELEVATION].value, units=M,
                          measures=climb[CLIMB_ELEVATION].measures_as_model(date)),
                    [value('Distance', climb[CLIMB_DISTANCE].value, units=M),
                     value('Time', climb[CLIMB_TIME].value, units=S)]]
                   for climb in climbs]

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

    def _display_schedule(self, s, f, date, schedule):
        all = []
        start, finish = local_date_to_time(schedule.start_of_frame(date)), local_date_to_time(schedule.next_frame(date))
        for group in s.query(ActivityGroup). \
                join(ActivityJournal, ActivityJournal.activity_group_id == ActivityGroup.id). \
                join(StatisticJournal, StatisticJournal.source_id == ActivityJournal.id). \
                join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
                filter(StatisticName.name == ACTIVE_TIME,
                       StatisticJournal.time >= start,
                       StatisticJournal.time < finish).all():
            columns = list(self.__schedule_fields(s, f, date, schedule, group))
            if columns:
                all.append(Pile([Text(group.name),
                                 Indent(Pile(columns))]))
        if all:
            yield Pile([Text('Activities'),
                        Indent(Pile(all))])

    def __schedule_fields(self, s, f, date, schedule, group):
        names = list(self.__names(s, group, ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED,
                                  TOTAL_CLIMB, CLIMB_ELEVATION, CLIMB_DISTANCE, CLIMB_GRADIENT, CLIMB_TIME))
        yield from summary_columns(s, f, date, schedule, names)
        names = self.__sort_names(self.__names_like(s, group, MIN_KM_TIME_ANY))
        yield from summary_columns(s, f, date, schedule, names)
        names = self.__sort_names(self.__names_like(s, group, MED_KM_TIME_ANY))
        yield from summary_columns(s, f, date, schedule, names)
        names = self.__sort_names(self.__names_like(s, group, MAX_MED_HR_M_ANY))
        yield from summary_columns(s, f, date, schedule, names)

    def __names(self, s, group, *names):
        for name in names:
            yield s.query(StatisticName). \
                filter(StatisticName.name == name,
                       StatisticName.owner == ActivityCalculator,
                       StatisticName.constraint == group).one()

    def __names_like(self, s, group, name):
        return s.query(StatisticName). \
            filter(StatisticName.name.like(name),
                   StatisticName.owner == ActivityCalculator,
                   StatisticName.constraint == group).all()
