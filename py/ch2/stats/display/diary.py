
from logging import getLogger

from sqlalchemy import or_

from . import Displayer
from ...diary.model import text, from_field, optional_text
from ...sql import DiaryTopicJournal, DiaryTopic

log = getLogger(__name__)


class DiaryDisplayer(Displayer):

    @optional_text('Diary')
    def _read_date(self, s, date):
        journal = DiaryTopicJournal.get_or_add(s, date)
        for topic in s.query(DiaryTopic).filter(DiaryTopic.parent == None,
                                                or_(DiaryTopic.start <= date, DiaryTopic.start == None),
                                                or_(DiaryTopic.finish >= date, DiaryTopic.finish == None)). \
                order_by(DiaryTopic.sort).all():
            if topic.schedule.at_location(date):
                yield list(self.__read_date_diary_topic(s, date, journal.cache(s), topic))

    def __read_date_diary_topic(self, s, date, cache, topic):
        yield text(topic.name)
        if topic.description: yield text(topic.description)
        log.debug(f'topic id {topic.id}; fields {topic.fields}')
        for field in topic.fields:
            if field.schedule.at_location(date):
                yield from_field(field, cache[field])
        for child in topic.children:
            if child.schedule.at_location(date):
                content = list(self.__read_date_diary_topic(s, date, cache, child))
                if content:
                    # single entries are just text fields
                    if len(content) == 1:
                        yield content[0]
                    else:
                        yield content

    def _read_schedule(self, s, date, schedule):
        return
        yield
