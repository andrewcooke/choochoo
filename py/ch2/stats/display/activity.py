
import datetime as dt
from logging import getLogger
from re import search

from sqlalchemy import or_, distinct
from sqlalchemy.orm.exc import NoResultFound

from . import JournalDiary
from ..calculate.activity import ActivityCalculator
from ..calculate.power import PowerCalculator
from ..names import ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED, MED_KM_TIME_ANY, MAX_MED_HR_M_ANY, CLIMB_ELEVATION, \
    CLIMB_DISTANCE, CLIMB_GRADIENT, CLIMB_TIME, TOTAL_CLIMB, MIN_KM_TIME_ANY, CALORIE_ESTIMATE, \
    ENERGY_ESTIMATE, MEAN_POWER_ESTIMATE, MAX_MEAN_PE_M_ANY, FITNESS_D_ANY, FATIGUE_D_ANY, _d, M, S, PERCENT_IN_Z_ANY
from ..read.segment import SegmentReader
from ...data.climb import climbs_for_activity
from ...diary.database import summary_column
from ...diary.model import text, value, optional_text, from_field
from ...lib.date import format_seconds, time_to_local_time, to_time, HMS, local_date_to_time, to_date, MONTH, add_date, \
    time_to_local_date, YMD
from ...sql import ActivityGroup, ActivityJournal, StatisticJournal, StatisticName, ActivityTopic, ActivityTopicJournal, \
    ActivityTopicField

log = getLogger(__name__)


class ActivityDiary(JournalDiary):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    def _read_journal_date(self, s, ajournal, date):
        yield text(self.__title(s, ajournal), tag='activity')
        yield from self.__read_activity_topics(s, ajournal, date)
        yield from self.__read_details(s, ajournal, date)

    def __read_activity_topics(self, s, ajournal, date):
        tjournal = ActivityTopicJournal.get_or_add(s, ajournal.file_hash)
        cache = tjournal.cache(s)
        # special case parentless fields
        for field in s.query(ActivityTopicField). \
                filter(ActivityTopicField.activity_topic == None). \
                order_by(ActivityTopicField.sort).all():
            yield from_field(field, cache[field])
        for topic in s.query(ActivityTopic). \
                filter(ActivityTopic.parent == None,
                       or_(ActivityTopic.activity_group_id == None,
                           ActivityTopic.activity_group_id == ajournal.activity_group.id)). \
                order_by(ActivityTopic.sort).all():
            yield list(self.__read_activity_topic(s, date, cache, topic))

    def __read_activity_topic(self, s, date, cache, topic):
        yield text(topic.name)
        if topic.description: yield text(topic.description)
        log.debug(f'topic id {topic.id}; fields {topic.fields}')
        for field in topic.fields:
            yield from_field(field, cache[field])
        for child in topic.children:
            if child.schedule.at_location(date):
                content = list(self.__read_activity_topic(s, date, cache, child))
                if content: yield content

    def __read_details(self, s, ajournal, date):
        zones = list(self.__read_zones(s, ajournal))
        if zones: yield [text('HR Zones (% time)')] + zones
        active_data = list(self.__read_active_data(s, ajournal, date))
        if active_data: yield [text('Activity Statistics')] + active_data
        climbs = list(self.__read_climbs(s, ajournal, date))
        if climbs: yield [text('Climbs')] + climbs
        for (title, template, re) in (('Min Time', MIN_KM_TIME_ANY, r'(\d+km)'),
                                      ('Med Time', MED_KM_TIME_ANY, r'(\d+km)'),
                                      ('Max Med Heart Rate', MAX_MED_HR_M_ANY, r'(\d+m)'),
                                      ('Max Mean Power Estimate', MAX_MEAN_PE_M_ANY, r'(\d+m)')):
            model = list(self.__read_template(s, ajournal, template, re, date))
            if model: yield [text(title)] + model

    @staticmethod
    def __read_zones(s, ajournal):
        percent_times = s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticJournal.time == ajournal.start,
                   StatisticName.name.like(PERCENT_IN_Z_ANY),
                   StatisticName.owner == ActivityCalculator,
                   StatisticName.constraint == ajournal.activity_group) \
            .order_by(StatisticName.name).all()
        if percent_times:
            for zone, percent_time in reversed(list(enumerate((time.value for time in percent_times), start=1))):
                yield [value('Zone', zone, tag='hr-zone'), value('Percent time', percent_time)]

    @staticmethod
    def __title(s, ajournal):
        title = f'{ajournal.name} ({ajournal.activity_group.name}'
        kits = s.query(StatisticJournal). \
            join(StatisticName). \
            filter(StatisticJournal.source == ajournal,
                   StatisticName.name == 'kit',
                   StatisticName.owner == SegmentReader).all()
        if kits:
            title += '/' + ','.join(str(kit.value) for kit in kits)
        return title + ')'

    @staticmethod
    def __read_active_data(s, ajournal, date):
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

    @staticmethod
    def __read_climbs(s, ajournal, date):
        total, climbs = climbs_for_activity(s, ajournal)
        if total:
            yield value('Total', total.value, measures=total.measures_as_model(date), units=M, tag='total-climb')
            for climb in climbs:
                yield [text('Climb'),
                       value('Elevation', climb[CLIMB_ELEVATION].value, units=M,
                             measures=climb[CLIMB_ELEVATION].measures_as_model(date)),
                       value('Distance', climb[CLIMB_DISTANCE].value, units=M),
                       value('Time', climb[CLIMB_TIME].value, units=S)]

    def __read_template(self, s, ajournal, template, re, date):
        sjournals = s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticJournal.time == ajournal.start,
                   StatisticName.name.like(template),
                   StatisticName.owner == ActivityCalculator,
                   StatisticName.constraint == ajournal.activity_group).order_by(StatisticName.name).all()
        for sjournal in self.__sort_journals(sjournals):
            yield value(search(re, sjournal.statistic_name.name).group(1), sjournal.value,
                        units=sjournal.statistic_name.units, measures=sjournal.measures_as_model(date))

    @staticmethod
    def __sort_journals(sjournals):
        return sorted(sjournals,
                      # order by integer embedded in name
                      key=lambda sjournal: int(search(r'(\d+)', sjournal.statistic_name.name).group(1)))

    @staticmethod
    def __sort_names(statistic_names):
        return sorted(statistic_names,
                      # order by integer embedded in name
                      key=lambda statistic_name: int(search(r'(\d+)', statistic_name.name).group(1)))

    @optional_text('Activities', tag='activity')
    def _read_schedule(self, s, date, schedule):
        start, finish = local_date_to_time(schedule.start_of_frame(date)), local_date_to_time(schedule.next_frame(date))
        for group in s.query(ActivityGroup). \
                join(ActivityJournal, ActivityJournal.activity_group_id == ActivityGroup.id). \
                join(StatisticJournal, StatisticJournal.source_id == ActivityJournal.id). \
                join(StatisticName, StatisticJournal.statistic_name_id == StatisticName.id). \
                filter(StatisticName.name == ACTIVE_TIME,
                       StatisticJournal.time >= start,
                       StatisticJournal.time < finish).all():
            fields = list(self.__read_schedule_fields(s, date, schedule, group))
            if fields:
                yield [text(group.name)] + fields

    @staticmethod
    def __names(s, group, *names):
        for name in names:
            try:
                yield s.query(StatisticName). \
                    filter(StatisticName.name == name,
                           StatisticName.owner == ActivityCalculator,
                           StatisticName.constraint == group).one()
            except NoResultFound:
                log.warning(f'Missing "{name}" in database')

    @staticmethod
    def __names_like(s, group, name):
        return s.query(StatisticName). \
            filter(StatisticName.name.like(name),
                   StatisticName.owner == ActivityCalculator,
                   StatisticName.constraint == group).all()

    def __read_schedule_fields(self, s, start, schedule, group):
        for name in self.__names(s, group, ACTIVE_DISTANCE, ACTIVE_TIME, ACTIVE_SPEED,
                                 TOTAL_CLIMB, CLIMB_ELEVATION, CLIMB_DISTANCE, CLIMB_GRADIENT, CLIMB_TIME):
            column = list(summary_column(s, schedule, start, name))
            if column: yield column
        for name in self.__sort_names(self.__names_like(s, group, MIN_KM_TIME_ANY)):
            column = list(summary_column(s, schedule, start, name))
            if column: yield column
        for name in self.__sort_names(self.__names_like(s, group, MED_KM_TIME_ANY)):
            column = list(summary_column(s, schedule, start, name))
            if column: yield column
        for name in self.__sort_names(self.__names_like(s, group, MAX_MED_HR_M_ANY)):
            column = list(summary_column(s, schedule, start, name))
            if column: yield column


def active_days(s, month):
    month_start = to_date(month)
    month_end = add_date(month_start, (1, MONTH))
    start = local_date_to_time(month_start)
    end = local_date_to_time(month_end)
    times = s.query(distinct(ActivityJournal.start)). \
        filter(ActivityJournal.start >= start,
               ActivityJournal.start < end).all()
    return [time_to_local_date(row[0]).strftime(YMD) for row in times]
