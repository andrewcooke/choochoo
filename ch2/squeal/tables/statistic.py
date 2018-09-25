from types import SimpleNamespace

from sqlalchemy import Column, Integer, ForeignKey, Text, UniqueConstraint, Float, inspect
from sqlalchemy.orm import relationship, backref

from ..support import Base
from ..types import Epoch, Cls
from ...lib.date import format_duration


# classes that add "raw" (underived) values must:
# 1 - do so with a statistic that references themselves (they can use cls_constraint for extra state)
# 2 - clean up when necessary (eg activity diary must delete values it "owns" if a diary entry is deleted)
# 3 - delete any intervals affected by changes (call SummaryStatistics.delete_around())

# classes that add "derived" values that depend on a single value must:
# 1 - set the StatisticDiary.statistic_diary_id to identify the "source"
# with that, values should be deleted on cascade when the source is deleted
# 2 - clean out Statistic entries if no longer used

# classes that add "derived" values that depend on a range of values must:
# 1 - define a suitable interval
# 2 - set the StatisticDiary.statistic_interval_id to identify the interval
# wuth that, values should be deleted on cascade when data are modified (and intervals deleted)

# similarly, classes that add ranks should add an interval and define StatisticRank.statistic_interval_id


class Statistic(Base):

    __tablename__ = 'statistic'

    id = Column(Integer, primary_key=True)
    cls = Column(Cls, nullable=False)  # class name of owner / creator
    cls_constraint = Column(Integer)  # eg activity for activity_diary (possibly null)
    name = Column(Text, nullable=False)  # simple, displayable name
    units = Column(Text)
    best = Column(Text)  # max, min etc (possibly comma-separated?)
    display = Column(Text)  # some desc of widget?  value range?
    UniqueConstraint('cls', 'cls_constraint')


class StatisticDiary(Base):

    __tablename__ = 'statistic_diary'

    id = Column(Integer, primary_key=True)
    statistic_id = Column(Integer, ForeignKey('statistic.id', ondelete='cascade'), nullable=False)
    statistic = relationship('Statistic')
    value = Column(Float)
    time = Column(Epoch, nullable=False)
    statistic_diary_id = Column(Integer,  # often null
                                ForeignKey('statistic_diary.id', ondelete='cascade'))
    statistic_interval_id = Column(Integer,  # often null
                                   ForeignKey('statistic_interval.id', ondelete='cascade'))
    interval = relationship('statistic_interval_id')
    UniqueConstraint('statistic_id', 'time')

    @property
    def fmt_value(self):
        units = self.statistic.units
        if not units:
            return '%s' % self.value
        elif units == 'm':
            if self.value > 2000:
                return '%.1fkm' % (self.value / 1000)
            else:
                return '%dm' % int(self.value)
        elif units == 's':
            return format_duration(self.value)
        elif units == 'km/h':
            return '%.1fkm/h' % self.value
        elif units == '%':
            return '%.1f%%' % self.value
        elif units == 'bpm':
            return '%dbpm' % int(self.value)
        else:
            return '%s%s' % (self.value, units)

    def __str__(self):
        return '%s: %s' % (self.statistic.name, self.fmt_value)


class StatisticInterval(Base):

    __tablename__ = 'statistic_interval'

    id = Column(Integer, primary_key=True)
    start = Column(Epoch)
    value = Column(Integer)  # null if open (null unit too), otherwise number of days etc (see units)
    units = Column(Text)   # 'm', 'd' etc
    UniqueConstraint('start', 'value', 'units')


class StatisticRank(Base):

    __tablename__ = 'statistic_rank'

    id = Column(Integer, primary_key=True)
    statistic_diary_id = Column(Integer, ForeignKey('statistic_diary.id', ondelete='cascade'), nullable=False)
    diary = relationship('statistic_diary_id',
                         backref=backref('ranks', cascade='all, delete-orphan', passive_deletes=True))
    statistic_interval_id = Column(Integer, ForeignKey('statistic_interval.id', ondelete='cascade'), nullable=False)
    interval = relationship('statistic_interval_id')
    rank = Column(Integer, nullable=False)  # 1 is best
    percentile = Column(Float, nullable=False)  # 100 is best
