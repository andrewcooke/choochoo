import datetime as dt
from json import dumps
from logging import getLogger

from pendulum.tz import get_local_timezone
from sqlalchemy import Column, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, backref

from .source import SourceType, Interval, UngroupedSource, GroupedSource
from .statistic import StatisticJournal, STATISTIC_JOURNAL_CLASSES
from .system import SystemConstant
from ..support import Base
from ..types import Json, Sched, Sort
from ..utils import add
from ...common.date import local_date_to_time
from ...common.sql import Date
from ...lib.schedule import Schedule

log = getLogger(__name__)


class Topic:
    '''
    A topic groups together a set of fields.  At it's simplest, think of it as a title in the diary.
    Topics can contain child topics, giving a tree-like structure, but relationships must be defined in
    concrete classes.
    '''

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False, server_default='')
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

    def __init__(self, id=None, parent=None, parent_id=None, schedule=None, title=None, description=None, sort=None):
        # Topic instances are only created in config.  so we intercept here to
        # duplicate data for start and finish - it's not needed elsewhere.
        if not isinstance(schedule, Schedule):
            schedule = Schedule(schedule)
        self.id = id
        self.parent = parent
        self.parent_id = parent_id
        self.schedule = schedule
        self.title = title
        self.description = description
        self.sort = sort
        self.start = schedule.start
        self.finish = schedule.finish

    def __str__(self):
        return 'DiaryTopic "%s" (%s)' % (self.title, self.schedule)


class ActivityTopic(Base, Topic):

    __tablename__ = 'activity_topic'

    parent_id = Column(Integer, ForeignKey('activity_topic.id'), nullable=True)
    activity_group_id = Column(Integer, ForeignKey('activity_group.id', ondelete='cascade'), nullable=True)
    activity_group = relationship('ActivityGroup')

    ROOT = 'Root'
    ROOT_DESCRIPTION = 'The root topic for all activities (should not be displayed).'

    @declared_attr
    def children(cls):
        # http://docs.sqlalchemy.org/en/latest/orm/self_referential.html
        return relationship('ActivityTopic', backref=backref('parent', remote_side=[cls.id]))

    def __str__(self):
        return 'ActivityTopic "%s" (%s)' % (self.title, self.activity_group)


class TopicField:

    id = Column(Integer, primary_key=True)
    sort = Column(Sort, nullable=False, server_default='0')
    model = Column(Json, nullable=False, server_default=dumps({}))

    @declared_attr
    def statistic_name_id(cls):
        # https://stackoverflow.com/questions/24666261/sqlalchemy-mixins-foreignkeys-and-declared-attr
        return Column(Integer, ForeignKey('statistic_name.id', ondelete='cascade'), nullable=False)

    @declared_attr
    def statistic_name(cls):
        return relationship('StatisticName')


class DiaryTopicField(Base, TopicField):

    # diary topic fields are associated with statistics whose constraints are the diary topic.
    # this lets us use the same name under different 'headings'.

    __tablename__ = 'diary_topic_field'

    diary_topic_id = Column(Integer, ForeignKey('diary_topic.id', ondelete='cascade'), nullable=False)
    diary_topic = relationship('DiaryTopic',
                               backref=backref('fields', cascade='all, delete-orphan',
                                               passive_deletes=True,
                                               order_by='DiaryTopicField.sort'))
    schedule = Column(Sched, nullable=False, server_default='')
    UniqueConstraint('statistic_name_id')

    def __str__(self):
        return 'DiaryTopicField "%s"/"%s"' % (self.diary_topic.title, self.statistic_name.name)


class ActivityTopicField(Base, TopicField):

    # activity topic fields are associated with statistics whose constraints are the activity group.
    # this correlates to some extent with the activity topic, which is also specific to an activity group
    # (so you will never see a field for group X if it has parent activity for group Y).

    NAME_DESCRIPTION = 'The title for the activity.'

    __tablename__ = 'activity_topic_field'

    activity_topic_id = Column(Integer, ForeignKey('activity_topic.id', ondelete='cascade'), nullable=False)
    activity_topic = relationship('ActivityTopic',
                                  backref=backref('fields', cascade='all, delete-orphan',
                                                  passive_deletes=True,
                                                  order_by='ActivityTopicField.sort'))
    UniqueConstraint('statistic_name_id')

    def __str__(self):
        name = self.activity_topic.title if self.activity_topic else None
        return f'ActivityTopicField {name} / {self.statistic_name.name}'


class Cache:

    def __init__(self, s, source, time, query):
        self.__session = s
        self.__source = source
        self.__time = time
        self.__cache = {field_id: statistic for field_id, statistic in query.all()}

    def __getitem__(self, field):
        if field.id not in self.__cache:
            log.debug(f'Creating {field}')
            name = field.statistic_name
            self.__cache[field.id] = add(self.__session,
                                         STATISTIC_JOURNAL_CLASSES[name.statistic_journal_type](
                                             statistic_name=name, source=self.__source, time=self.__time))
        log.debug(f'Returning {field}')
        return self.__cache[field.id]

    def __len__(self):
        return len(self.__cache)


class DiaryTopicJournal(UngroupedSource):

    __tablename__ = 'diary_topic_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    date = Column(Date, nullable=False, index=True)
    UniqueConstraint(date)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.DIARY_TOPIC
    }

    @classmethod
    def get_or_add(cls, s, date):
        instance = s.query(DiaryTopicJournal).filter(DiaryTopicJournal.date == date).one_or_none()
        if not instance:
            instance = add(s, DiaryTopicJournal(date=date))
        return instance

    def cache(self, s):
        return Cache(s, self, local_date_to_time(self.date),
                     s.query(DiaryTopicField.id, StatisticJournal).
                     filter(DiaryTopicField.statistic_name_id == StatisticJournal.statistic_name_id,
                            StatisticJournal.source_id == self.id))

    def __str__(self):
        return 'DiaryTopicJournal from %s' % self.date

    @classmethod
    def check_tz(cls, data, s):
        tz = get_local_timezone()
        db_tz = data.get_constant(SystemConstant.TIMEZONE, none=True)
        if db_tz is None:
            db_tz = data.set_constant(SystemConstant.TIMEZONE, '')
        if db_tz != tz.name:
            cls.__reset_timezone(s)
            data.set_constant(SystemConstant.TIMEZONE, tz.name, force=True)

    @classmethod
    def __reset_timezone(cls, s):
        log.warning('Timezone has changed')
        log.warning('Recalculating times for TopicJournal entries')
        for tj in s.query(DiaryTopicJournal).all():
            tj.time = local_date_to_time(tj.date)
        Interval.dirty_all(s)

    def time_range(self, s):
        start = local_date_to_time(self.date)
        return start, start + dt.timedelta(days=1)


class ActivityTopicJournal(GroupedSource):

    __tablename__ = 'activity_topic_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    file_hash_id = Column(Integer, ForeignKey('file_hash.id'),
                          nullable=False, index=True, unique=True)
    file_hash = relationship('FileHash', backref=backref('activity_topic_journal', uselist=False))

    __mapper_args__ = {
        'polymorphic_identity': SourceType.ACTIVITY_TOPIC
    }

    @classmethod
    def get_or_add(cls, s, file_hash, activity_group):
        instance = s.query(ActivityTopicJournal).filter(ActivityTopicJournal.file_hash == file_hash).one_or_none()
        if not instance:
            instance = add(s, ActivityTopicJournal(file_hash=file_hash, activity_group=activity_group))
        return instance

    def cache(self, s):
        return Cache(s, self, self.file_hash.activity_journal.start,
                     s.query(ActivityTopicField.id, StatisticJournal).
                     filter(ActivityTopicField.statistic_name_id == StatisticJournal.statistic_name_id,
                            StatisticJournal.source_id == self.id))

    def time_range(self, s):
        return None, None


