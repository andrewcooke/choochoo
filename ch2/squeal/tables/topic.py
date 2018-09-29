
from functools import total_ordering

from sqlalchemy import Column, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref

from .source import SourceType, Source
from ..support import Base
from ..types import Ordinal
from ...lib.schedule import Specification
from ch2.squeal.tables.statistic import StatisticMixin


@total_ordering
class Topic(Base):

    __tablename__ = 'topic'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('schedule.id'), nullable=True)
    # http://docs.sqlalchemy.org/en/latest/orm/self_referential.html
    children = relationship('Schedule', backref=backref('parent', remote_side=[id]))
    repeat = Column(Text, nullable=False, server_default='')
    start = Column(Ordinal)
    finish = Column(Ordinal)
    name = Column(Text, nullable=False, server_default='', unique=True)
    description = Column(Text, nullable=False, server_default='')
    has_notes = Column(Boolean, nullable=False, server_default='0')
    sort = Column(Text, nullable=False, server_default='')

    def specification(self):
        # allow for empty repeat, but still support start / finish
        spec = Specification(self.repeat if self.repeat else 'd')
        spec.start = self.start
        spec.finish = self.finish
        return spec

    def at_location(self, date):
        if date:
            return self.specification().frame().at_location(date)
        else:
            return True

    def __repr__(self):
        text = '%s: %s (parent %s; children %s)' % \
               (self.id, self.name, self.parent.id if self.parent else None, [c.id for c in self.children])
        if self.repeat or self.start or self.finish:
            text += ' %s' % self.specification()
        return text

    # todo - rethink this to work on different levels?
    def comparison(self):
        return self.sort, self.name

    def __lt__(self, other):
        if isinstance(other, Topic):
            return self.comparison() < other.comparison()
        else:
            raise NotImplemented

    def __eq__(self, other):
        return isinstance(other, Topic) and other.id == self.id

    @classmethod
    def query_root(cls, session, date=None):
        root_topics = list(session.query(Topic).filter(Topic.parent_id == None).all())
        if date is not None:
            root_topics = [schedule for schedule in root_topics if schedule.at_location(date)]
        return list(sorted(root_topics))


class TopicJournal(StatisticMixin, Source):

    __tablename__ = 'topic_journal'

    date = Column(Ordinal, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topic.id'), primary_key=True)
    topic = relationship('Topic')
    notes = Column(Text, nullable=False, server_default='')

    __mapper_args__ = {
        'polymorphic_identity': SourceType.TOPIC
    }

