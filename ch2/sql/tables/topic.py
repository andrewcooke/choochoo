
import datetime as dt
from json import dumps
from logging import getLogger

from pendulum.tz import get_local_timezone
from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, backref

from .source import SourceType, Source, Interval
from .statistic import StatisticJournal, STATISTIC_JOURNAL_CLASSES
from .system import SystemConstant
from ..support import Base
from ..types import Date, Cls, Json, Sched, Sort
from ...lib.data import assert_attr
from ...lib.date import local_date_to_time
from ...lib.schedule import Schedule

log = getLogger(__name__)


class Topic:
    '''
    A topic groups together a set of fields.  At it's simplest, think of it as a title in the diary.
    Topics can contain child topics, giving a tree-like structure, but relationships must be defined in
    concrete classes.
    '''

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, server_default='')
    description = Column(Text, nullable=False, server_default='')
    sort = Column(Sort, nullable=False, server_default='0')


class DiaryTopic(Base, Topic):
    '''
    DiaryTopics are associated with a schedule, which means that may only be displayed on certain dates.
    '''

    __tablename__ = 'diary_topic'

    parent_id = Column(Integer, ForeignKey('diary_topic.id'), nullable=True)
    schedule = Column(Sched, nullable=False)
    start = Column(Date)
    finish = Column(Date)

    @declared_attr
    def children(cls):
        # http://docs.sqlalchemy.org/en/latest/orm/self_referential.html
        return relationship('DiaryTopic', backref=backref('parent', remote_side=[cls.id]))

    def __init__(self, id=None, parent=None, parent_id=None, schedule=None, name=None, description=None, sort=None):
        # Topic instances are only created in config.  so we intercept here to
        # duplicate data for start and finish - it's not needed elsewhere.
        if not isinstance(schedule, Schedule):
            schedule = Schedule(schedule)
        self.id = id
        self.parent = parent
        self.parent_id = parent_id
        self.schedule = schedule
        self.name = name
        self.description = description
        self.sort = sort
        self.start = schedule.start
        self.finish = schedule.finish

    def __str__(self):
        return 'DiaryTopic "%s" (%s)' % (self.name, self.schedule)


class ActivityTopic(Base, Topic):

    __tablename__ = 'activity_topic'

    parent_id = Column(Integer, ForeignKey('activity_topic.id'), nullable=True)
    activity_group_id = Column(Integer, ForeignKey('activity_group.id'), nullable=False)
    activity_group = relationship('ActivityGroup')

    @declared_attr
    def children(cls):
        # http://docs.sqlalchemy.org/en/latest/orm/self_referential.html
        return relationship('ActivityTopic', backref=backref('parent', remote_side=[cls.id]))

    def __str__(self):
        return 'ActivityTopic "%s" (%s)' % (self.name, self.activity_group)


class TopicField:

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)  # StatisticJournalType
    sort = Column(Sort, nullable=False, server_default='0')
    display_cls = Column(Cls, nullable=False)
    display_args = Column(Json, nullable=False, server_default=dumps(()))
    display_kargs = Column(Json, nullable=False, server_default=dumps({}))

    @declared_attr
    def statistic_name_id(cls):
        return Column(Integer, ForeignKey('statistic_name.id', ondelete='cascade'), nullable=False)

    @declared_attr
    def statistic_name(cls):
        return relationship('StatisticName')


class DiaryTopicField(Base, TopicField):

    __tablename__ = 'diary_topic_field'

    diary_topic_id = Column(Integer, ForeignKey('diary_topic.id', ondelete='cascade'), nullable=False)
    diary_topic = relationship('DiaryTopic',
                               backref=backref('fields', cascade='all, delete-orphan',
                                               passive_deletes=True,
                                               order_by='DiaryTopicField.sort'))
    schedule = Column(Sched, nullable=False, server_default='')

    def __str__(self):
        return 'DiaryTopicField "%s"/"%s"' % (self.diary_topic.name, self.statistic_name.name)


class ActivityTopicField(Base, TopicField):

    __tablename__ = 'activity_topic_field'

    activity_topic_id = Column(Integer, ForeignKey('activity_topic.id', ondelete='cascade'), nullable=False)
    activity_topic = relationship('ActivityTopic',
                                  backref=backref('fields', cascade='all, delete-orphan',
                                                  passive_deletes=True,
                                                  order_by='ActivityTopicField.sort'))

    def __str__(self):
        return 'ActivityTopicField "%s"/"%s"' % (self.activity_topic.name, self.statistic_name.name)


class DiaryTopicJournal(Source):

    __tablename__ = 'diary_topic_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    diary_topic_id = Column(Integer, ForeignKey('diary_topic.id'))
    diary_topic = relationship('DiaryTopic')
    date = Column(Date, nullable=False, index=True)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.DIARY_TOPIC
    }

    def populate(self, s):
        if hasattr(self, 'statistics'):
            return
        assert_attr(self, 'date')
        if self.id is None:
            s.flush([self])
        log.debug('Populating journal for topic %s at %s' % (self.diary_topic.name, self.date))
        self.statistics = {}
        for field in self.diary_topic.fields:
            assert_attr(field, 'schedule')
            if field.schedule.at_location(self.date):
                log.debug('Finding StatisticJournal for field %s' % field.statistic_name.name)
                journal = StatisticJournal.at_date(s, self.date, field.statistic_name.name,
                                                   field.statistic_name.owner, self.diary_topic)
                if not journal:
                    journal = STATISTIC_JOURNAL_CLASSES[field.type](
                        statistic_name=field.statistic_name, source=self, time=local_date_to_time(self.date))
                    s.add(journal)
                self.statistics[field] = journal

    def __str__(self):
        return 'DiaryTopicJournal from %s' % self.date

    @classmethod
    def check_tz(cls, s):
        tz = get_local_timezone()
        db_tz = SystemConstant.get(s, SystemConstant.TIMEZONE, none=True)
        if not db_tz:
            db_tz = SystemConstant.set(s, SystemConstant.TIMEZONE, '')
        if db_tz != tz.name:
            cls.__reset_timezone(s)
            SystemConstant.set(s, SystemConstant.TIMEZONE, tz.name, force=True)

    @classmethod
    def __reset_timezone(cls, s):
        log.warning('Timezone has changed')
        log.warning('Recalculating times for TopicJournal entries')
        for tj in s.query(DiaryTopicJournal).all():
            tj.time = local_date_to_time(tj.date)
        Interval.delete_all(s)

    def time_range(self, s):
        start = local_date_to_time(self.date)
        return start, start + dt.timedelta(days=1)
