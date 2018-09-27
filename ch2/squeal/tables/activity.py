
from sqlalchemy import Column, Text, Integer, ForeignKey, Float, UniqueConstraint
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, backref

from .diary import BaseDiary
from ..support import Base
from ..types import Epoch
from ...stoats.database import StatisticMixin


class FileScan(Base):

    __tablename__ = 'file_scan'

    path = Column(Text, nullable=False, primary_key=True)
    last_scan = Column(Integer, nullable=False)  # unix epoch


class Activity(Base):

    __tablename__ = 'activity'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, server_default='')
    description = Column(Text, nullable=False, server_default='')
    sort = Column(Text, nullable=False, server_default='')


class ActivityDiary(StatisticMixin, BaseDiary):

    __tablename__ = 'activity_diary'
    __statistic_constraint__ = 'activity_id'

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey('activity.id'), nullable=False)
    activity = relationship('Activity')
    name = Column(Text, unique=True)
    fit_file = Column(Text, nullable=False, unique=True)
    finish = Column(Epoch, nullable=False)
    notes = Column(Text)

    __mapper_args__ = {
        'polymorphic_identity': 'activity',
    }


class ActivityTimespan(Base):

    __tablename__ = 'activity_timespan'

    id = Column(Integer, primary_key=True)
    activity_diary_id = Column(Integer, ForeignKey('activity_diary.id', ondelete='cascade'),
                               nullable=False)
    activity_diary = relationship('ActivityDiary',
                                  backref=backref('timespans', cascade='all, delete-orphan',
                                                  passive_deletes=True,
                                                  order_by='ActivityTimespan.start',
                                                  collection_class=ordering_list('start')))
    start = Column(Float, nullable=False)  # unix epoch
    finish = Column(Float, nullable=False)  # unix epoch
    UniqueConstraint('activity_diary_id', 'start')


class ActivityWaypoint(Base):

    __tablename__ = 'activity_waypoint'

    activity_diary_id = Column(Integer, ForeignKey('activity_diary.id', ondelete='cascade'),
                               nullable=False, primary_key=True)
    activity_diary = relationship('ActivityDiary',
                                  backref=backref('waypoints', cascade='all, delete-orphan',
                                                  passive_deletes=True,
                                                  order_by='ActivityWaypoint.epoch',
                                                  collection_class=ordering_list('epoch')))
    activity_timespan_id = Column(Integer, ForeignKey('activity_timespan.id'))
    activity_timespan = relationship('ActivityTimespan',
                                     backref=backref('waypoints',
                                                     order_by='ActivityWaypoint.epoch',
                                                     collection_class=ordering_list('epoch')))
    epoch = Column(Float, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    heart_rate = Column(Integer)
    distance = Column(Float)
    speed = Column(Float)
