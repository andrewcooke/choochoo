from functools import total_ordering

from sqlalchemy import Column, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref

from ..lib.repeating import Specification
from .types import Ordinal
from .support import Base


class ScheduleType(Base):

    __tablename__ = 'schedule_type'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, server_default='')
    sort = Column(Text, nullable=False, server_default='')


@total_ordering
class Schedule(Base):

    __tablename__ = 'schedule'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('schedule.id'), nullable=True)
    # http://docs.sqlalchemy.org/en/latest/orm/self_referential.html
    children = relationship('Schedule', backref=backref('parent', remote_side=[id]))
    type_id = Column(Integer, ForeignKey('schedule_type.id'))
    type = relationship('ScheduleType')
    repeat = Column(Text, nullable=False, server_default='')
    start = Column(Ordinal)
    finish = Column(Ordinal)
    title = Column(Text, nullable=False, server_default='')
    description = Column(Text, nullable=False, server_default='')
    has_notes = Column(Boolean, nullable=False, server_default='0')
    sort = Column(Text, nullable=False, server_default='')

    def at_location(self, ordinals):
        if ordinals:
            # allow for empty repeat, but still support start / finish
            spec = Specification(self.repeat if self.repeat else 'd')
            spec.start = self.start
            spec.finish = self.finish
            return spec.frame().at_location(ordinals)
        else:
            return True

    def __repr__(self):
        return '%d: %s (parent %s; children %s)' % \
               (self.id, self.title, self.parent.id if self.parent else None, [c.id for c in self.children])

    @property
    def comparison(self):
        return self.type.sort, self.type.name, self.sort, self.title

    def __lt__(self, other):
        if isinstance(other, Schedule):
            return other.comparison < self.comparison
        else:
            raise NotImplemented

    def __eq__(self, other):
        return isinstance(other, Schedule) and other.id == self.id


class ScheduleDiary(Base):

    __tablename__ = 'schedule_diary'

    date = Column(Ordinal, primary_key=True)
    schedule_id = Column(Integer, ForeignKey('schedule.id'), primary_key=True)
    notes = Column(Text, nullable=False, server_default='')
