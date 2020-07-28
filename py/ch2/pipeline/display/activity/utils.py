import datetime as dt
from logging import getLogger
from re import search

from sqlalchemy import or_, distinct, desc

from ..utils import Displayer, ActivityJournalDelegate
from ...calculate import SummaryCalculator
from ...calculate.activity import ActivityCalculator
from ...calculate.power import PowerCalculator
from ....common.date import YMD_HM, HM, format_minutes, add_date, MONTH, YMD, YEAR, YM
from ....common.log import log_current_exception
from ....data.climb import climbs_for_activity
from ....diary.database import interval_column
from ....diary.model import optional_text, text, from_field, value
from ....lib import local_date_to_time, time_to_local_time, to_time, to_date, time_to_local_date
from ....names import Names as N
from ....sql import ActivityGroup, ActivityJournal, ActivityTopicJournal, ActivityTopicField, StatisticName, \
    ActivityTopic, StatisticJournal, Pipeline, PipelineType, Interval

log = getLogger(__name__)


class ActivityDisplayer(Displayer):

    @optional_text('Activities')
    def _read_date(self, s, date):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        for activity_group in s.query(ActivityGroup).order_by(ActivityGroup.sort).all():
            for ajournal in s.query(ActivityJournal). \
                    filter(ActivityJournal.finish >= start,
                           ActivityJournal.start < finish,
                           ActivityJournal.activity_group == activity_group). \
                    order_by(ActivityJournal.start).all():
                yield list(self._single_activity(s, ajournal, date))

    def _single_activity(self, s, ajournal, date):
        yield text(self.__title(s, ajournal), tag='activity-title', db=ajournal)
        yield from self._read_journal_date(s, ajournal, date)

    @staticmethod
    def __title(s, ajournal):
        return '%s - %s  (%s) %s' % (time_to_local_time(to_time(ajournal.start), fmt=YMD_HM),
                                     time_to_local_time(to_time(ajournal.finish), fmt=HM),
                                     format_minutes((ajournal.finish - ajournal.start).seconds),
                                     ajournal.activity_group.name)

    def _read_journal_date(self, s, ajournal, date):
        for pipeline in Pipeline.all_instances(s, PipelineType.DISPLAY_ACTIVITY):
            try:
                if pipeline.interpolate:
                    yield from pipeline.read_journal_date(s, ajournal, date)
                else:
                    entry = list(pipeline.read_journal_date(s, ajournal, date))
                    if entry: yield entry
            except Exception as e:
                log.warning(f'Error calling {pipeline}')
                log_current_exception(traceback=True)

    @optional_text('Activities')
    def _read_schedule(self, s, date, schedule):
        intervals = s.query(Interval).join(ActivityGroup). \
            filter(Interval.schedule == schedule,
                   Interval.start == date).all()
        intervals = sorted(intervals, key=lambda i: i.activity_group.name if i.activity_group else '')
        for interval in intervals:
            pipelines = list(self._read_pipelines(s, interval))
            if pipelines:
                yield [text(interval.activity_group.name, tag='activity-group')] + pipelines

    def _read_pipelines(self, s, interval):
        for pipeline in Pipeline.all_instances(s, PipelineType.DISPLAY_ACTIVITY):
            try:
                 results = list(pipeline.read_interval(s, interval))
                 if results: yield results
            except Exception as e:
                log.warning(f'Error calling {pipeline} with {interval}')
                log_current_exception(traceback=True)


class ActivityDelegate(ActivityJournalDelegate):

    def __init__(self, *args, **kargs):
        super().__init__(interpolate=True, *args, **kargs)

    def read_journal_date(self, s, ajournal, date):
        yield list(self._read_journal_topics(s, ajournal, date))
        yield from self.__read_details(s, ajournal, date)

    def _read_journal_topics(self, s, ajournal, date):
        yield text('Activity', db=ajournal)
        yield from self.__read_activity_topics(s, ajournal, date)

    def __read_activity_topics(self, s, ajournal, date):
        tjournal = ActivityTopicJournal.get_or_add(s, ajournal.file_hash, ajournal.activity_group)
        cache = tjournal.cache(s)
        # special case root
        for field in s.query(ActivityTopicField). \
                join(ActivityTopic). \
                filter(ActivityTopic.title == ActivityTopic.ROOT,
                       or_(ActivityTopic.activity_group_id == None,
                           ActivityTopic.activity_group_id == ajournal.activity_group.id)). \
                order_by(ActivityTopicField.sort).all():
            yield from_field(field, cache[field])
        for topic in s.query(ActivityTopic). \
                filter(ActivityTopic.parent == None,
                       ActivityTopic.title != ActivityTopic.ROOT,
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
            if child.activity_group == topic.activity_group and child.schedule.at_location(date):
                content = list(self.__read_activity_topic(s, date, cache, child))
                if content: yield content

    def __read_details(self, s, ajournal, date):
        zones = list(self.__read_zones(s, ajournal))
        if zones: yield [text('HR Zones (% time)')] + zones
        active_data = list(self.__read_active_data(s, ajournal, date))
        if active_data: yield [text('Activity Statistics')] + active_data
        climbs = list(self.__read_climbs(s, ajournal, date))
        if climbs: yield [text('Climbs')] + climbs
        for (title, template, re) in (('Min Time', N.MIN_KM_TIME_ANY, r'(\d+km)'),
                                      ('Med Time', N.MED_KM_TIME_ANY, r'(\d+km)'),
                                      ('Max Med Heart Rate', N.MAX_MED_HR_M_ANY, r'(\d+m)'),
                                      ('Max Mean Power Estimate', N.MAX_MEAN_PE_M_ANY, r'(\d+m)')):
            model = list(self.__read_template(s, ajournal, template, re, date))
            if model: yield [text(title)] + model

    @staticmethod
    def __read_zones(s, ajournal):
        percent_times = s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticJournal.time == ajournal.start,
                   StatisticName.name.like(N.PERCENT_IN_Z_ANY),
                   StatisticName.owner == ActivityCalculator) \
            .order_by(StatisticName.name).all()
        if percent_times:
            for zone, percent_time in reversed(list(enumerate((time.value for time in percent_times), start=1))):
                yield [value('Zone', zone, tag='hr-zone'), value('Percent time', percent_time)]

    @staticmethod
    def __read_active_data(s, ajournal, date):
        for name in (N.ACTIVE_DISTANCE, N.ACTIVE_TIME, N.ACTIVE_SPEED, N.MEAN_POWER_ESTIMATE):
            sjournal = StatisticJournal.at(s, ajournal.start, name, ActivityCalculator, ajournal.activity_group)
            if sjournal:
                yield value(sjournal.statistic_name.title, sjournal.value,
                            units=sjournal.statistic_name.units,
                            measures=sjournal.measures_as_model(date))
        for name in (N._delta(N.FITNESS_ANY), N._delta(N.FATIGUE_ANY),
                     N.EARNED_D_ANY, N.RECOVERY_D_ANY):
            for sjournal in StatisticJournal.at_like(s, ajournal.start, name, ActivityCalculator,
                                                     ajournal.activity_group):
                yield value(sjournal.statistic_name.title, sjournal.value,
                            units=sjournal.statistic_name.units,
                            measures=sjournal.measures_as_model(date))
        for name in (N.ENERGY_ESTIMATE, N.CALORIE_ESTIMATE):
            sjournal = StatisticJournal.at(s, ajournal.start, name, PowerCalculator, ajournal.activity_group)
            if sjournal:
                yield value(sjournal.statistic_name.title, sjournal.value,
                            units=sjournal.statistic_name.units,
                            measures=sjournal.measures_as_model(date))

    @classmethod
    def __sjournal_as_value(cls, sjournal, date=None):
        measures = sjournal.measures_as_model(date) if date else None
        return value(sjournal.statistic_name.title, sjournal.value,
                     units=sjournal.statistic_name.units, measures=measures)

    @classmethod
    def __climb_as_value(cls, climb, key, date=None):
        return cls.__sjournal_as_value(climb[key], date=date)

    @classmethod
    def __read_climbs(cls, s, ajournal, date):
        total, climbs = climbs_for_activity(s, ajournal)
        if total:
            yield cls.__sjournal_as_value(total, date=date)
            for climb in climbs:
                yield [text('Climb'),
                       cls.__climb_as_value(climb, N.CLIMB_ELEVATION, date=date),
                       cls.__climb_as_value(climb, N.CLIMB_DISTANCE),
                       cls.__climb_as_value(climb, N.CLIMB_TIME),
                       cls.__climb_as_value(climb, N.CLIMB_GRADIENT)]

    def __read_template(self, s, ajournal, template, re, date):
        sjournals = s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticJournal.time == ajournal.start,
                   StatisticName.name.like(template),
                   StatisticName.owner == ActivityCalculator).order_by(StatisticName.name).all()
        for sjournal in self.__sort_journals(sjournals):
            if sjournal.value > 0:  # avoid zero power and anything else with silly value
                yield value(search(re, sjournal.statistic_name.title).group(1), sjournal.value,
                            units=sjournal.statistic_name.units, measures=sjournal.measures_as_model(date))

    @staticmethod
    def __sort_journals(sjournals):
        return sorted(sjournals,
                      # order by integer embedded in name
                      key=lambda sjournal: int(search(r'(\d+)', sjournal.statistic_name.title).group(1)))

    @staticmethod
    def __sort_names(names):
        # order by integer embedded in name
        return sorted(names, key=lambda name: int(search(r'(\d+)', name).group(1)))


    @optional_text('Activities', tag='activity')
    def read_interval(self, s, interval):
        for name in (N.ACTIVE_DISTANCE, N.ACTIVE_TIME, N.ACTIVE_SPEED, N.TOTAL_CLIMB, N.CLIMB_ELEVATION,
                     N.CLIMB_DISTANCE, N.CLIMB_GRADIENT, N.CLIMB_TIME):
            column = list(interval_column(s, interval, name, SummaryCalculator))
            if column: yield column
        for template in (N.MIN_KM_TIME_ANY, N.MED_KM_TIME_ANY, N.MAX_MED_HR_M_ANY):
            for name in self.__sort_names(self.__names_like(s, template)):
                column = list(interval_column(s, interval, name, SummaryCalculator))
                if column: yield column

    @staticmethod
    def __names_like(s, name):
        return [statistic_name.name
                for statistic_name in s.query(StatisticName).
                    filter(StatisticName.name.like(name),
                           StatisticName.owner == ActivityCalculator).all()]


def active_dates(s, start, range, fmt):
    date_start = to_date(start)
    date_end = add_date(date_start, (1, range))
    time_start = local_date_to_time(date_start)
    time_end = local_date_to_time(date_end)
    times = s.query(distinct(ActivityJournal.start)). \
        filter(ActivityJournal.start >= time_start,
               ActivityJournal.start < time_end).all()
    return list(set(time_to_local_date(row[0]).strftime(fmt) for row in times))


def active_days(s, month):
    return active_dates(s, month, MONTH, YMD)


def active_months(s, year):
    return active_dates(s, year, YEAR, YM)


def latest_activity(s):
    return s.query(ActivityJournal). \
        order_by(desc(ActivityJournal.start)).limit(1).one_or_none()


def activity_times_by_group(s):
    by_group = {}
    for group in s.query(ActivityGroup).all():
        activities = [time_to_local_time(activity.start)
                      for activity in s.query(ActivityJournal).
                          filter(ActivityJournal.activity_group == group).
                          order_by(desc(ActivityJournal.start)).all()]
        if activities:
            by_group[group.name] = activities
    return by_group
