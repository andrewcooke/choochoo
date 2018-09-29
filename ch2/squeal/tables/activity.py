
from sqlalchemy import Column, Text, Integer, ForeignKey, Float, UniqueConstraint
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, backref

from .source import Source, SourceType
from ..support import Base
from ..types import Epoch


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


class ActivityJournal(Source):

    __tablename__ = 'activity_journal'
    __statistic_constraint__ = 'activity_id'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    activity_id = Column(Integer, ForeignKey('activity.id'), nullable=False)
    activity = relationship('Activity')
    name = Column(Text, unique=True)
    fit_file = Column(Text, nullable=False, unique=True)
    finish = Column(Epoch, nullable=False)
    notes = Column(Text)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.ACTIVITY
    }


class ActivityTimespan(Base):

    __tablename__ = 'activity_timespan'

    id = Column(Integer, primary_key=True)
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'),
                                 nullable=False)
    activity_journal = relationship('ActivityJournal',
                                    backref=backref('timespans', cascade='all, delete-orphan',
                                                    passive_deletes=True,
                                                    order_by='ActivityTimespan.start',
                                                    collection_class=ordering_list('start')))
    start = Column(Epoch, nullable=False)
    finish = Column(Epoch, nullable=False)
    UniqueConstraint('activity_journal_id', 'start')


class ActivityWaypoint(Base):

    __tablename__ = 'activity_waypoint'

    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'),
                                 nullable=False, primary_key=True)
    activity_journal = relationship('ActivityJournal',
                                    backref=backref('waypoints', cascade='all, delete-orphan',
                                                    passive_deletes=True,
                                                    order_by='ActivityWaypoint.time',
                                                    collection_class=ordering_list('time')))
    activity_timespan_id = Column(Integer, ForeignKey('activity_timespan.id'))
    activity_timespan = relationship('ActivityTimespan',
                                     backref=backref('waypoints',
                                                     order_by='ActivityWaypoint.time',
                                                     collection_class=ordering_list('time')))
    time = Column(Float, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    heart_rate = Column(Integer)
    distance = Column(Float)
    speed = Column(Float)
