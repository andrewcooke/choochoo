
from logging import getLogger

from sqlalchemy import or_

from . import Displayer
from ..calculate.summary import SummaryCalculator
from ...diary.model import text, from_field, optional_text, value, trim_no_stats
from ...sql import DiaryTopicJournal, DiaryTopic, StatisticJournal

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

    @optional_text('Diary')
    @trim_no_stats
    def _read_schedule(self, s, date, schedule):
        finish = schedule.next_frame(date)
        for topic in s.query(DiaryTopic).filter(DiaryTopic.parent == None,
                                                or_(DiaryTopic.start < finish, DiaryTopic.start == None),
                                                or_(DiaryTopic.finish >= date, DiaryTopic.finish == None)). \
                order_by(DiaryTopic.sort).all():
            yield list(self.__read_schedule_topic(s, schedule, date, finish, topic))

    def __read_schedule_topic(self, s, schedule, start, finish, topic):
        yield text(topic.name)
        if topic.description: yield text(topic.description)
        for field in topic.fields:
            column = list(self.__summary_column(s, schedule, start, field.statistic_name))
            if column: yield column
        for child in topic.children:
            if (child.start is None or child.start < finish) and (child.finish is None or child.finish > start):
                content = list(self.__read_schedule_topic(s, schedule, start, finish, child))
                if content: yield content


    def __summary_column(self, s, schedule, start, name):
        journals = StatisticJournal.at_interval(s, start, schedule, SummaryCalculator, name, SummaryCalculator)
        for named, journal in enumerate(journal for journal in journals if journal.value != 0):
            summary, period, name = SummaryCalculator.parse_name(journal.statistic_name.name)
            if not named:
                yield text(name)
            yield value(summary, journal.value, units=journal.statistic_name.units)
