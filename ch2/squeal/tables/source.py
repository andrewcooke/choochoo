
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
        from ...stoats.summary import SummaryStatistics  # avoid import loop
        intervals = set()
        for always, instances in [(True, session.new), (False, session.dirty), (True, session.deleted)]:
            # wipe the containing intervals if this is a source that has changed in some way
            # and it's not an interval itself
            sources = [instance for instance in instances
                       if (isinstance(instance, Source) and
                           not isinstance(instance, Interval) and
                           instance.time is not None and
                           (always or session.is_modified(instance)))]
            intervals |= set(chain(*[SummaryStatistics.intervals_including(Epoch.to_time(source.time))
                                     for source in sources]))
        for start, (value, units) in intervals:
            interval = session.query(Interval). \
                filter(Interval.time == start,
                       Interval.value == value,
                       Interval.units == units).one_or_none()
            if interval:
                session.delete(interval)


@listens_for(Session, 'before_flush')
def clear_intervals(session, context, instances):
    Source.clear_intervals(session)


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
