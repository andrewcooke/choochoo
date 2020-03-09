
from logging import getLogger

from sqlalchemy import or_

from .model import from_field, text, optional_text, link, value, trim_no_stats
from ..lib import format_date, time_to_local_time
from ..lib.date import YMD
from ..sql import DiaryTopic, DiaryTopicJournal, ActivityJournal, StatisticJournal
from ..stats.calculate.summary import SummaryCalculator
from ..stats.display import read_pipeline
from ..stats.display.nearby import fmt_nearby, nearby_any_time

log = getLogger(__name__)

COMPARE_LINKS = 'compare-links'


def read_date(s, date):
    yield text(date.strftime('%Y-%m-%d - %A'), tag='title')
    topics = list(read_date_diary_topics(s, date))
    if topics: yield topics
    yield from read_pipeline(s, date)
    gui = list(read_gui(s, date))
    if gui: yield gui


@optional_text('Diary')
def read_date_diary_topics(s, date):
    journal = DiaryTopicJournal.get_or_add(s, date)
    for topic in s.query(DiaryTopic).filter(DiaryTopic.parent == None,
                                            or_(DiaryTopic.start <= date, DiaryTopic.start == None),
                                            or_(DiaryTopic.finish >= date, DiaryTopic.finish == None)). \
            order_by(DiaryTopic.sort).all():
        if topic.schedule.at_location(date):
            yield list(read_date_diary_topic(s, date, journal.cache(s), topic))


def read_date_diary_topic(s, date, cache, topic):
    yield text(topic.name)
    if topic.description: yield text(topic.description)
    log.debug(f'topic id {topic.id}; fields {topic.fields}')
    for field in topic.fields:
        if field.schedule.at_location(date):
            yield from_field(field, cache[field])
    for child in topic.children:
        if child.schedule.at_location(date):
            content = list(read_date_diary_topic(s, date, cache, child))
            if content:
                # single entries are just text fields
                if len(content) == 1:
                    yield content[0]
                else:
                    yield content


@optional_text('Jupyter')
def read_gui(s, date):
    for aj1 in ActivityJournal.at_date(s, date):
        yield list(read_activity_gui(s, aj1))
    yield link('Health', db=(format_date(date),))


def read_activity_gui(s, aj1):
    yield text('aj1.name', tag='jupyter-activity')
    links = [link('None', db=(time_to_local_time(aj1.start), None, aj1.activity_group.name))] + \
            [link(fmt_nearby(aj2, nb),
                  db=(time_to_local_time(aj1.start), time_to_local_time(aj2.start), aj1.activity_group.name))
             for aj2, nb in nearby_any_time(s, aj1)]
    yield [text('%s v ' % 'aj1.name', tag=COMPARE_LINKS)] + links
    yield link('All Similar', db=(time_to_local_time(aj1.start), aj1.activity_group.name))


def read_schedule(s, schedule, date):
    yield text(date.strftime(YMD) + ' - Summary for %s' % schedule.describe(), tag='title')
    topics = list(read_schedule_topics(s, schedule, date))
    if topics: yield topics
    yield from read_pipeline(s, date, schedule=schedule)
    gui = list(read_schedule_gui(s, schedule, date))
    if gui: yield gui


@optional_text('Diary')
@trim_no_stats
def read_schedule_topics(s, schedule, start):
    finish = schedule.next_frame(start)
    for topic in s.query(DiaryTopic).filter(DiaryTopic.parent == None,
                                            or_(DiaryTopic.start < finish, DiaryTopic.start == None),
                                            or_(DiaryTopic.finish >= start, DiaryTopic.finish == None)). \
            order_by(DiaryTopic.sort).all():
        yield list(read_schedule_topic(s, schedule, start, finish, topic))


def read_schedule_topic(s, schedule, start, finish, topic):
    yield text(topic.name)
    if topic.description: yield text(topic.description)
    for field in topic.fields:
        column = list(summary_column(s, schedule, start, field.statistic_name))
        if column: yield column
    for child in topic.children:
        if (child.start is None or child.start < finish) and (child.finish is None or child.finish > start):
            content = list(read_schedule_topic(s, schedule, start, finish, child))
            if content: yield content


def summary_column(s, schedule, start, name):
    journals = StatisticJournal.at_interval(s, start, schedule, SummaryCalculator, name, SummaryCalculator)
    for named, journal in enumerate(journals):
        summary, period, name = SummaryCalculator.parse_name(journal.statistic_name.name)
        if not named:
            yield text(name)
        yield value(summary, journal.value, units=journal.statistic_name.units)


@optional_text('Jupyter')
def read_schedule_gui(s, schedule, start):
    finish = schedule.next_frame(start)
    yield link('All Activities', db=(format_date(start), format_date(finish)))
