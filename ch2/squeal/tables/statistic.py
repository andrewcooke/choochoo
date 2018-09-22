
from sqlalchemy import Column, Integer, ForeignKey, Text, UniqueConstraint, Float
from sqlalchemy.orm import relationship

from ..support import Base
from ..types import Epoch
from ...lib.date import format_duration


class Statistic(Base):

    __tablename__ = 'statistic'

    id = Column(Integer, primary_key=True)
    cls = Column(Text, nullable=False)
    cls_constraint = Column(Integer)
    name = Column(Text, nullable=False)
    namespace = Column(Text, nullable=False)
    units = Column(Text)
    best = Column(Text)  # max, min etc (possibly comma-separated?)
    UniqueConstraint('cls', 'cls_constraint')
    UniqueConstraint('name', 'namespace')


class StatisticDiary(Base):

    __tablename__ = 'statistic_diary'

    id = Column(Integer, primary_key=True)
    statistic_id = Column(Integer, ForeignKey('statistic.id'), nullable=False)
    statistic = relationship('Statistic')
    value = Column(Float)
    time = Column(Epoch, nullable=False)
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
