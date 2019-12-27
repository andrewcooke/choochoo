
from logging import getLogger

from sqlalchemy import or_

from .model import from_field, text, optional_text, link
from ..lib import time_to_local_time, to_date
from ..sql import DiaryTopic, DiaryTopicJournal, ActivityJournal
from ..sql.utils import add
from ..stats.display import read_pipeline
from ..stats.display.nearby import fmt_nearby, nearby_any_time

log = getLogger(__name__)

COMPARE_LINKS = 'compare-links'


def read_daily(s, date):
    yield text(date.strftime('%Y-%m-%d - %A'), tag='title')
    topics = list(read_daily_topics(s, date))
    if topics: yield topics
    yield from read_pipeline(s, date)
    gui = list(read_gui(s, date))
    if gui: yield gui


@optional_text('Diary')
def read_daily_topics(s, date):
    for topic in s.query(DiaryTopic).filter(DiaryTopic.parent == None,
                                            or_(DiaryTopic.start <= date, DiaryTopic.start == None),
                                            or_(DiaryTopic.finish >= date, DiaryTopic.finish == None)). \
            order_by(DiaryTopic.sort).all():
        if topic.schedule.at_location(date):
            yield list(read_daily_topic(s, date, topic))


def read_daily_topic(s, date, topic):
    yield text(topic.name)
    if topic.description: yield text(topic.description)
    journal = s.query(DiaryTopicJournal). \
        filter(DiaryTopicJournal.diary_topic == topic,
               DiaryTopicJournal.date == date).one_or_none()
    if not journal:
        journal = add(s, DiaryTopicJournal(diary_topic=topic, date=date))
    journal.populate(s)
    log.debug(f'topic id {topic.id}; fields {topic.fields}')
    for field in topic.fields:
        if field.schedule.at_location(date):
            yield from_field(field, journal.statistics[field])
    for child in topic.children:
        if child.schedule.at_location(date):
            content = list(read_daily_topic(s, date, child))
            if content: yield content


@optional_text('Jupyter')
def read_gui(s, date):
    for aj1 in ActivityJournal.at_date(s, date):
        yield list(read_activity_gui(s, aj1))
    yield link('Health', db=date)


def read_activity_gui(s, aj1):
    yield text(aj1.name)
    links = [link('None', db=(aj1, None))] + \
            [link(fmt_nearby(aj2, nb), db=(aj1, aj2)) for aj2, nb in nearby_any_time(s, aj1)]
    yield [text('%s v ' % aj1.name, tag=COMPARE_LINKS)] + links
    yield link('All Similar', db=aj1)
