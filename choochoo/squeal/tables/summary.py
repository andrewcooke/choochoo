
from sqlalchemy import Column, Integer, ForeignKey, Float, UniqueConstraint, Text
from sqlalchemy.orm import relationship, backref

from .activity import ActivityStatistic
from .statistic import Statistic
from ..support import Base
from ..types import Ordinal


class Summary(Base):

    __tablename__ = 'summary'

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey('activity.id', ondelete='cascade'),
                         nullable=False)
    activity = relationship('Activity')
    type = Column(Text, nullable=False)  #  month / year / custom
    UniqueConstraint('activity_id')


class SummaryTimespan(Base):

    __tablename__ = 'summary_timespan'

    id = Column(Integer, primary_key=True)
    summary_id = Column(Integer, ForeignKey('summary.id', ondelete='cascade'),
                        nullable=False)
    summary = relationship('Summary',
                           backref=backref('timespans',
                                           cascade='all, delete-orphan', passive_deletes=True))
    start = Column(Ordinal)  # inclusive (eg start of this month)
    finish = Column(Ordinal)  # exclusive (eg start of next month)
    created = Column(Integer, nullable=False)  # unix epoch
    total_activities = Column(Integer, nullable=False)
    total_distance = Column(Float, nullable=False)
    total_time = Column(Float, nullable=False)


class RankingStatistic(Base):

    __tablename__ = 'ranking_statistic'

    id = Column(Integer, primary_key=True)
    summary_timespan_id = Column(Integer, ForeignKey('summary_timespan.id', ondelete='cascade'),
                                 nullable=False)
    summary_timespan = relationship('SummaryTimespan',
                                    backref=backref('rankings',
                                                    cascade='all, delete-orphan', passive_deletes=True))
    activity_statistic_id = Column(Integer, ForeignKey('activity_statistic.id', ondelete='cascade'),
                                   nullable=False)
    activity_statistic = relationship('ActivityStatistic',
                                      backref=backref('ranking', uselist=False,
                                                      cascade='all, delete-orphan', passive_deletes=True))
    rank = Column(Integer, nullable=False)  # 1, 2, 3...
    percentile = Column(Float, nullable=False)  # [0, 100)


class DistributionStatistic(Base):

    __tablename__ = 'distribution_statistic'

    id = Column(Integer, primary_key=True)
    summary_timespan_id = Column(Integer, ForeignKey('summary_timespan.id', ondelete='cascade'),
                                 nullable=False)
    summary_timespan = relationship('SummaryTimespan',
                                    backref=backref('distributions',
                                                    cascade='all, delete-orphan', passive_deletes=True))
    statistic_id = Column(Integer, ForeignKey('statistic.id', ondelete='cascade'),
                          nullable=False)
    statistic = relationship(Statistic)
    percentile = Column(Integer, nullable=False)  # 0, 25, 50, 75, 100
    activity_statistic_id = Column(Integer, ForeignKey('activity_statistic.id', ondelete='cascade'),
                                   nullable=False)
    activity_statistic = relationship(ActivityStatistic)
    UniqueConstraint('summary_id', 'statistic_id')
