
from enum import IntEnum

from sqlalchemy import ForeignKey, Column, Integer, Text
from sqlalchemy.orm import relationship

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
