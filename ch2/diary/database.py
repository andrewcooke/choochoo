
from logging import getLogger

from sqlalchemy import or_

from .model import from_field, text
from ..sql import DiaryTopic, DiaryTopicJournal
from ..sql.utils import add
from ..stats.display import read_pipeline

log = getLogger(__name__)


'''
This package deals with serializing diary data and moving it between the database and the presentation layer.

The data can be in several different formats, all of which have the same high level (nested) structure and
which can be iterated over together.
'''


def read_daily(s, date):
    yield text(date.strftime('%Y-%m-%d - %A'))
    yield list(read_daily_topics(s, date))
    yield from read_pipeline(s, date)


def read_daily_topics(s, date):
    for topic in s.query(DiaryTopic).filter(DiaryTopic.parent == None,
                                            or_(DiaryTopic.start <= date, DiaryTopic.start == None),
                                            or_(DiaryTopic.finish >= date, DiaryTopic.finish == None)). \
            order_by(DiaryTopic.sort).all():
        if topic.schedule.at_location(date):
            yield text(topic.name)
            content = list(read_daily_topic(s, date, topic))
            if content: yield content


def read_daily_topic(s, date, topic):
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
            yield text(child.name)
            content = list(read_daily_topic(s, date, child))
            if content: yield content
