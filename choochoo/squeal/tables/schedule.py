
from functools import total_ordering

from sqlalchemy import Column, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref

from ..support import Base
from ..types import Ordinal
from ...lib.date import format_date
from ...lib.repeating import Specification


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
    # type is used only for top-level parents (where parent_id is NULL)
    type_id = Column(Integer, ForeignKey('schedule_type.id'))
    type = relationship('ScheduleType')
    repeat = Column(Text, nullable=False, server_default='')
    start = Column(Ordinal)
    finish = Column(Ordinal)
    title = Column(Text, nullable=False, server_default='')
    description = Column(Text, nullable=False, server_default='')
    has_notes = Column(Boolean, nullable=False, server_default='0')
    sort = Column(Text, nullable=False, server_default='')

    @property
    def specification(self):
        # allow for empty repeat, but still support start / finish
        spec = Specification(self.repeat if self.repeat else 'd')
        spec.start = self.start
        spec.finish = self.finish
        return spec

    def at_location(self, date):
        if date:
            return self.specification.frame().at_location(date)
        else:
            return True

    def __repr__(self):
        text = '%s: %s (parent %s; children %s)' % \
               (self.id, self.title, self.parent.id if self.parent else None, [c.id for c in self.children])
        if self.repeat or self.start or self.finish:
            text += ' %s' % self.specification
        return text

    @property
    def comparison(self):
        return self.type.sort if self.type else '', self.type.name if self.type else '', self.sort, self.title

    def __lt__(self, other):
        if isinstance(other, Schedule):
            return self.comparison < other.comparison
        else:
            raise NotImplemented

    def __eq__(self, other):
        return isinstance(other, Schedule) and other.id == self.id

    @classmethod
    def query_root(cls, session, date=None, type_id=None):
        query = session.query(Schedule).filter(Schedule.parent_id == None)
        if type_id is not None:
            query = query.filter(Schedule.type_id == type_id)
        root_schedules = list(query.all())
        if date is not None:
            root_schedules = [schedule for schedule in root_schedules if schedule.at_location(date)]
        return list(sorted(root_schedules))


class ScheduleDiary(Base):

    __tablename__ = 'schedule_diary'

    date = Column(Ordinal, primary_key=True)
    schedule_id = Column(Integer, ForeignKey('schedule.id'), primary_key=True)
    schedule = relationship('Schedule')
    notes = Column(Text, nullable=False, server_default='')

    def __repr__(self):
        return'%s: %s (schedule %s)' % (format_date(self.date), self.notes, self.schedule_id)
