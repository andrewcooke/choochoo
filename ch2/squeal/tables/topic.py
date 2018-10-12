
from json import dumps

from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.event import listens_for
from sqlalchemy.orm import relationship, backref, Session

from .source import SourceType, Source
from .statistic import StatisticJournal, STATISTIC_JOURNAL_CLASSES
from ..support import Base
from ..types import Ordinal, Cls, Json, Sched, Sort
from ...lib.schedule import Schedule


class Topic(Base):

    __tablename__ = 'topic'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('topic.id'), nullable=True)
    # http://docs.sqlalchemy.org/en/latest/orm/self_referential.html
    children = relationship('Topic', backref=backref('parent', remote_side=[id]))
    schedule = Column(Sched, nullable=False)
    start = Column(Ordinal)
    finish = Column(Ordinal)
    name = Column(Text, nullable=False, server_default='')
    description = Column(Text, nullable=False, server_default='')
    sort = Column(Sort, nullable=False, server_default='')

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
        return 'Topic "%s" (%s)' % (self.name, self.schedule)

    def populate(self, s, date):
        self.journal = s.query(TopicJournal). \
            filter(TopicJournal.topic == self,
                   TopicJournal.time == date).one_or_none()
        if not self.journal:
            self.journal = TopicJournal(topic=self, time=date)
            s.add(self.journal)


class TopicField(Base):

    __tablename__ = 'topic_field'

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topic.id', ondelete='cascade'), nullable=False)
    topic = relationship('Topic',
                         backref=backref('fields', cascade='all, delete-orphan',
                                         passive_deletes=True,
                                         order_by='TopicField.sort'))
    type = Column(Integer, nullable=False)  # StatisticType
    sort = Column(Sort)
    statistic_id = Column(Integer, ForeignKey('statistic.id', ondelete='cascade'), nullable=False)
    statistic = relationship('Statistic')
    display_cls = Column(Cls, nullable=None)
    display_args = Column(Json, nullable=None, server_default=dumps(()))
    display_kargs = Column(Json, nullable=None, server_default=dumps({}))

    def __str__(self):
        return 'TopicField "%s"/"%s"' % (self.topic.name, self.statistic.name)


class TopicJournal(Source):

    __tablename__ = 'topic_journal'
    __statistic_constraint__ = 'topic_id'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    topic_id = Column(Integer, ForeignKey('topic.id'))
    topic = relationship('Topic')

    __mapper_args__ = {
        'polymorphic_identity': SourceType.TOPIC
    }

    def populate(self, s):
        if self.time is None:
            raise Exception('No time defined')
        self.statistics = {}
        for field in self.topic.fields:
            if self.id:
                journal = s.query(StatisticJournal). \
                    filter(StatisticJournal.source == self,
                           StatisticJournal.statistic == field.statistic).one_or_none()
            else:
                # we're not yet registered with the database so cannot search for matching
                # StatisticJournal entries.  either this is an error or (more likely!) we
                # did query, found nothing, and are creating a new entry.
                journal = None
            if not journal:
                journal = STATISTIC_JOURNAL_CLASSES[field.type](statistic=field.statistic, source=self)
                s.add(journal)
            self.statistics[field] = journal


@listens_for(Session, 'loaded_as_persistent')
@listens_for(Session, 'transient_to_pending')
def populate(session, instance):
    if isinstance(instance, TopicJournal):
        with session.no_autoflush:
            instance.populate(session)
