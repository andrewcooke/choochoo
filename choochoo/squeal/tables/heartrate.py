
from sqlalchemy import Column, Integer, ForeignKey, Float

from ..support import Base
from ..types import Ordinal


class HeartRateZones(Base):

    __tablename__ = 'heart_rate_zones'

    id = Column(Integer, primary_key=True)
    date = Column(Ordinal,nullable=False)


class HeartRateZone(Base):

    __tablename__ = 'heart_rate_zone'

    id = Column(Integer, primary_key=True)
    heart_rate_zones_id = Column(Integer, ForeignKey('heart_rate_zones.id'))
    hr_bpm = Column(Float, nullable=False)
    hr_zone = Column(Integer, nullable=False)
