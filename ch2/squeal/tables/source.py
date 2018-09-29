
from enum import Enum

from sqlalchemy import ForeignKey, Column, Integer, Text

from ..support import Base
from ..types import Epoch
from ...lib.date import add_duration


class SourceType(Enum):

    SOURCE = 0
    INTERVAL = 1
    ACTIVITY = 2
    TOPIC = 3


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

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), nullable=False)
    value = Column(Integer)  # null if open (null unit too), otherwise number of days etc (see units)
    units = Column(Text)   # 'm', 'd' etc

    __mapper_args__ = {
        'polymorphic_identity': SourceType.INTERVAL
    }

    def range(self):
        return self.time, add_duration(self.time, (self.value, self.units))
