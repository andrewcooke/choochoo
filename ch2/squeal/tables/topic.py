
from functools import total_ordering
from types import SimpleNamespace

from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship, backref

from .source import SourceType, Source
from .statistic import StatisticJournal, STATISTIC_JOURNAL_CLASSES
from ..support import Base
from ..types import Ordinal
from ...lib.date import to_datetime


# @total_ordering
class Topic(Base):

    __tablename__ = 'topic'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('topic.id'), nullable=True)
    # http://docs.sqlalchemy.org/en/latest/orm/self_referential.html
    children = relationship('Topic', backref=backref('parent', remote_side=[id]))
    repeat = Column(Text, nullable=False, server_default='')
    start = Column(Ordinal)
    finish = Column(Ordinal)
    name = Column(Text, nullable=False, server_default='', unique=True)
    description = Column(Text, nullable=False, server_default='')
    sort = Column(Text, nullable=False, server_default='')

    # def specification(self):
    #     # allow for empty repeat, but still support start / finish
    #     spec = Specification(self.repeat if self.repeat else 'd')
    #     spec.start = self.start
    #     spec.finish = self.finish
    #     return spec
    #
    # def at_location(self, date):
    #     if date:
    #         return self.specification().frame().at_location(date)
    #     else:
    #         return True
    #
    # def __repr__(self):
    #     text = '%s: %s (parent %s; children %s)' % \
    #            (self.id, self.name, self.parent.id if self.parent else None, [c.id for c in self.children])
    #     if self.repeat or self.start or self.finish:
    #         text += ' %s' % self.specification()
    #     return text
    #
    # # todo - rethink this to work on different levels?
    # def comparison(self):
    #     return self.sort, self.name
    #
    # def __lt__(self, other):
    #     if isinstance(other, Topic):
    #         return self.comparison() < other.comparison()
    #     else:
    #         raise NotImplemented
    #
    # def __eq__(self, other):
    #     return isinstance(other, Topic) and other.id == self.id
    #
    # @classmethod
    # def query_root(cls, session, date=None):
    #     root_topics = list(session.query(Topic).filter(Topic.parent_id == None).all())
    #     if date is not None:
    #         root_topics = [schedule for schedule in root_topics if schedule.at_location(date)]
    #     return list(sorted(root_topics))


class TopicStatistic(Base):

    __tablename__ = 'topic_statistic'

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topic.id', ondelete='cascade'), nullable=False)
    topic = relationship('Topic')
    type = Column(Integer, nullable=False)  # StatisticType
    statistic_id = Column(Integer, ForeignKey('statistic.id', ondelete='cascade'), nullable=False)
    statistic = relationship('Statistic')


class TopicJournal(Source):

    __tablename__ = 'topic_journal'
    __statistic_constraint__ = 'topic_id'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), nullable=False)
    topic_id = Column(Integer, ForeignKey('topic.id'), primary_key=True)
    topic = relationship('Topic')

    __mapper_args__ = {
        'polymorphic_identity': SourceType.TOPIC
    }

    def populate_statistics(self, session):
        if self.time is None:
            raise Exception('No time defined')
        self.statistics = SimpleNamespace()
        for statistic in session.query(TopicStatistic). \
                filter(TopicStatistic.topic == self.topic).all():
            journal = session.query(StatisticJournal). \
                filter(StatisticJournal.source == self,
                       StatisticJournal.time == self.time).one_or_none()
            if not journal:
                journal = STATISTIC_JOURNAL_CLASSES[statistic.type](statistic=statistic.statistic, source=self)
                session.add(journal)
            setattr(self.statistics, statistic.statistic.name, journal)

