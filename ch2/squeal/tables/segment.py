
from sqlalchemy import Column, Integer, ForeignKey, Float, Text
from sqlalchemy.orm import relationship

from ..support import Base


class SegmentJournal(Base):

    __tablename__ = 'segment_journal'

    id = Column(Integer, primary_key=True)
    segment_id = Column(Integer, ForeignKey('segment.id', ondelete='cascade'),
                        nullable=False, index=True)
    segment = relationship('Segment')
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'),
                                 nullable=False, index=True)
    activity_journal = relationship('ActivityJournal')


class Segment(Base):

    __tablename__ = 'segment'

    id = Column(Integer, primary_key=True)
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
