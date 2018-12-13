
from sqlalchemy import Column, Integer, ForeignKey, Float, Text, UniqueConstraint, or_
from sqlalchemy.orm import relationship

from .source import SourceType, Source
from ..support import Base
from ..types import Time
from ...lib.date import format_time


class SegmentJournal(Source):

    __tablename__ = 'segment_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    # do not use on delete cascade here since it leaves source entries without children
    # instead, to guarantee consistency, call clean()
    segment_id = Column(Integer, ForeignKey('segment.id', ondelete='set null'), index=True)
    segment = relationship('Segment')
    # do not use on delete cascade here since it leaves source entries without children
    # instead, to guarantee consistency, call clean()
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='set null'), index=True)
    activity_journal = relationship('ActivityJournal', foreign_keys=[activity_journal_id])
    start = Column(Time, nullable=False)
    finish = Column(Time, nullable=False)
    UniqueConstraint(segment_id, activity_journal_id, start, finish)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.SEGMENT
    }

    def __str__(self):
        return 'Segment Journal %s to %s' % (format_time(self.start), format_time(self.finish))

    def time_range(self, s):
        return self.start, self.finish

    @classmethod
    def clean(cls, s):
        q1 = s.query(SegmentJournal.id). \
                filter(or_(SegmentJournal.segment_id == None,
                           SegmentJournal.activity_journal_id == None)).cte()
        s.query(Source).filter(Source.id.in_(q1)).delete(synchronize_session=False)


class Segment(Base):

    __tablename__ = 'segment'

    id = Column(Integer, primary_key=True)
    # need this because (1) segments do depend on activity group and (2) we want separate stats
    # depending on segment/group so need this as a constraint.
    activity_group_id = Column(Integer, ForeignKey('activity_group.id'), nullable=False)
    activity_group = relationship('ActivityGroup')
    start_lat = Column(Float, nullable=False)
    start_lon = Column(Float, nullable=False)
    finish_lat = Column(Float, nullable=False)
    finish_lon = Column(Float, nullable=False)
    distance = Column(Float, nullable=False)
    name = Column(Text, nullable=False, index=True)
    description = Column(Text)

    @property
    def start(self):
        return self.start_lon, self.start_lat

    @start.setter
    def start(self, lon_lat):
        self.start_lon, self.start_lat = lon_lat

    @property
    def finish(self):
        return self.finish_lon, self.finish_lat

    @finish.setter
    def finish(self, lon_lat):
        self.finish_lon, self.finish_lat = lon_lat

    def coords(self, start):
        if start:
            return self.start
        else:
            return self.finish

    def __str__(self):
        return 'Segment "%s/%s"' % (self.name, self.activity_group.name)
