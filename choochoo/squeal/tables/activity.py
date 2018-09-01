
from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from ..support import Base
from ..types import Ordinal


class FileScan(Base):

    __tablename__ = 'file_scan'

    path = Column(Text, nullable=False, primary_key=True)
    last_scan = Column(Integer, nullable=False)  # unix epoch


class Activity(Base):

    __tablename__ = 'activity'

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False, server_default='')
    description = Column(Text, nullable=False, server_default='')
    sort = Column(Text, nullable=False, server_default='')


class ActivityDiary(Base):

    __tablename__ = 'activity_diary'

    id = Column(Integer, primary_key=True)
    date = Column(Ordinal, nullable=False)
    activity_id = Column(Integer, ForeignKey('activity.id'), nullable=False)
    activity = relationship('Activity')
    title = Column(Text)
    fit_file = Column(Text, nullable=False, unique=True)
    start = Column(DateTime, nullable=False)
    finish = Column(DateTime, nullable=False)


class ActivityWaypoint(Base):

    __tablename__ = 'activity_waypoint'

    activity_diary_id = Column(Integer, ForeignKey('activity_diary.id', ondelete='cascade'),
                               nullable=False, primary_key=True)
    activity_diary = relationship('ActivityDiary',
                                  backref=backref('waypoints', cascade='all, delete-orphan', passive_deletes=True))
    epoch = Column(Float, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    hr_bpm = Column(Integer)
    distance = Column(Float)
    speed = Column(Float)


class ActivityTimespan(Base):

    __tablename__ = 'activity_timespan'

    activity_diary_id = Column(Integer, ForeignKey('activity_diary.id', ondelete='cascade'),
                               nullable=False, primary_key=True)
    activity_diary = relationship('ActivityDiary',
                                  backref=backref('timespans', cascade='all, delete-orphan', passive_deletes=True))
    start = Column(Float, nullable=False, primary_key=True)  # unix epoch
    finish = Column(Float, nullable=False)  # unix epoch


class ActivityStatistic(Base):

    __tablename__ = 'activity_statistic'

    activity_diary_id = Column(Integer, ForeignKey('activity_diary.id', ondelete='cascade'),
                               nullable=False, primary_key=True)
    activity_diary = relationship('ActivityDiary',
                                  backref=backref('statistics', cascade='all, delete-orphan', passive_deletes=True))
    time = Column(Integer, nullable=False)  # unix epoch
    name = Column(Text, nullable=False)
    value = Column(Float, nullable=False)
    units = Column(Text, nullable=False, server_default='')
    UniqueConstraint('activity_diary_id', 'name')

