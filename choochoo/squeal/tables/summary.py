
from sqlalchemy import Column, Integer, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from .activity import ActivityStatistic, Statistic
from ..support import Base
from ..types import Ordinal


class Summary(Base):

    __tablename__ = 'summary'

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey('activity.id', ondelete='cascade'),
                         nullable=False)
    start = Column(Ordinal)  # inclusive (eg start of this month)
    finish = Column(Ordinal)  # exclusive (eg start of next month)
    created = Column(Integer, nullable=False)  # unix epoch
    total_activities = Column(Integer)
    total_distance = Column(Float)
    total_time = Column(Float)


class RankingStatistic(Base):

    __tablename__ = 'ranking_statistic'

    id = Column(Integer, primary_key=True)
    summary_id = Column(Integer, ForeignKey('summary.id', ondelete='cascade'),
                        nullable=False)
    summary = relationship('Summary')
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
    summary_id = Column(Integer, ForeignKey('summary.id', ondelete='cascade'),
                        nullable=False)
    summary = relationship('Summary')
    statistic_id = Column(Integer, ForeignKey('statistic.id', ondelete='cascade'),
                          nullable=False)
    statistic = relationship(Statistic)
    percentile = Column(Integer, nullable=False)  # 0, 25, 50, 75, 100
    activity_statistic_id = Column(Integer, ForeignKey('activity_statistic.id', ondelete='cascade'),
                                   nullable=False)
    activity_statistic = relationship(ActivityStatistic)
    UniqueConstraint('summary_id', 'statistic_id')
