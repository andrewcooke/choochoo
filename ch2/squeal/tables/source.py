
from enum import IntEnum
from itertools import chain

from sqlalchemy import ForeignKey, Column, Integer, Text
from sqlalchemy.event import listens_for
from sqlalchemy.orm import Session

from ..support import Base
from ..types import Epoch
from ...lib.date import add_duration


class SourceType(IntEnum):

    SOURCE = 0
    INTERVAL = 1
    ACTIVITY = 2
    TOPIC = 3
    CONSTANT = 4


class Source(Base):

    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)
    time = Column(Epoch, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.SOURCE,
        'polymorphic_on': type
    }

    @classmethod
    def clear_intervals(cls, session):
        from ...stoats.summary import SummaryProcess
        intervals = set()
        for instances in [session.new, session.dirty, session.deleted]:
            sources = [instance for instance in instances
                       if isinstance(instance, Source) and instance.time is not None]
            intervals |= set(chain(*[SummaryProcess.intervals_including(Epoch.to_time(source.time))
                                     for source in sources]))
        for start, (value, units) in intervals:
            interval = session.query(Interval).\
                filter(Interval.time == start,
                       Interval.value == value,
                       Interval.units == units).one_or_none()
            if interval:
                session.delete(interval)


class Interval(Source):

    __tablename__ = 'interval'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    value = Column(Integer)  # null if open (null unit too), otherwise number of days etc (see units)
    units = Column(Text)   # 'M', 'd' etc
    days = Column(Integer, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.INTERVAL
    }

    def range(self):
        return self.time, add_duration(self.time, (self.value, self.units))


@listens_for(Session, 'before_flush')
def populate(session, context, instances):
    Source.clear_intervals(session)
