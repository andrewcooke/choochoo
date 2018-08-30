
from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey, Float

from ..support import Base
from ..types import Ordinal


class DirectoryScan(Base):

    __tablename__ = 'directory_scan'

    directory = Column(Text, nullable=False, primary_key=True)
    last_scan = Column(DateTime, nullable=False)


class Activity(Base):

    __tablename__ = 'activity'

    id = Column(Integer, primary_key=True)
    fit_file = Column(Text, nullable=False)
    date = Column(Ordinal,nullable=False)
    start = Column(DateTime, nullable=False)
    finish = Column(DateTime, nullable=False)
    sport = Column(Text, nullable=False)
    title = Column(Text)


class ActivityData(Base):

    __tablename__ = 'activity_data'

    activity_id = Column(Integer, ForeignKey('activity.id'), nullable=False, primary_key=True)
    epoch = Column(Float, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    hr_bpm = Column(Integer)
    distance = Column(Float)
    speed = Column(Float)
