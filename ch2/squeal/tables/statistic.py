
from enum import Enum
from types import SimpleNamespace

from sqlalchemy import Column, Integer, ForeignKey, Text, UniqueConstraint, Float
from sqlalchemy.orm import relationship

from ..support import Base
from ..types import Cls
from ...lib.date import format_duration


class Statistic(Base):

    __tablename__ = 'statistic'

    id = Column(Integer, primary_key=True)
    cls = Column(Cls, nullable=False)  # class name of owner / creator / displayer
    # eg activity for activity_diary (possibly null, possibly index into more complex data)
    cls_constraint = Column(Integer)
    name = Column(Text, nullable=False)  # simple, displayable name
    description = Column(Text)
    units = Column(Text)
    summary = Column(Text)  # '[max]', '[min]' etc - can be multiple values but each in square brackets
    widget = Column(Text)  # some desc of widget?  value range?  null for pre-calculated / constant
    display = Column(Text)  # 'd', 'm', 'y' - what screen to display (null for no display)
    sort = Column(Text)  # sorting for display
    UniqueConstraint('cls', 'cls_constraint')


class StatisticType(Enum):

    STATISTIC = 0
    INTEGER = 1
    FLOAT = 2
    TEXT = 3


class StatisticJournal(Base):

    __tablename__ = 'statistic_journal'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)
    statistic_id = Column(Integer, ForeignKey('statistic.id', ondelete='cascade'), nullable=False)
    statistic = relationship('Statistic')
    source_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), nullable=False)
    source = relationship('Source')

    __mapper_args__ = {
        'polymorphic_identity': StatisticType.STATISTIC,
        'polymorphic_on': 'type'
    }

    @property
    def time(self):
        return self.source.time


class StatisticJournalInteger(StatisticJournal):

    __tablename__ = 'statistic_journal_integer'

    id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), primary_key=True)
    value = Column(Integer)

    __mapper_args__ = {
        'polymorphic_identity': StatisticType.INTEGER
    }

    def formatted(self):
        units = self.statistic.units
        if not units:
            return '%d' % self.value
        elif units == 'm':
            if self.value > 2000:
                return '%dkm' % (self.value / 1000)
            else:
                return '%dm' % self.value
        elif units == 's':
            return format_duration(self.value)
        elif units == 'km/h':
            return '%dkm/h' % self.value
        elif units == '%':
            return '%d%%' % self.value
        elif units == 'bpm':
            return '%dbpm' % self.value
        else:
            return '%d%s' % (self.value, units)


class StatisticJournalFloat(StatisticJournal):

    __tablename__ = 'statistic_journal_float'

    id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), primary_key=True)
    value = Column(Float)

    __mapper_args__ = {
        'polymorphic_identity': StatisticType.FLOAT
    }

    def formatted(self):
        units = self.statistic.units
        if not units:
            return '%f' % self.value
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


class StatisticJournalText(StatisticJournal):

    __tablename__ = 'statistic_journal_text'

    id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), primary_key=True)
    value = Column(Text)

    __mapper_args__ = {
        'polymorphic_identity': StatisticType.TEXT
    }

    def formatted(self):
        if not self.units:
            return '%s' % self.value
        else:
            return '%s%s' % (self.value, self.units)


class StatisticRank(Base):

    __tablename__ = 'statistic_rank'

    id = Column(Integer, primary_key=True)
    statistic_journal_id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), nullable=False)
    source_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), nullable=False)  # must be an interval
    rank = Column(Integer, nullable=False)  # 1 is best
    percentile = Column(Float, nullable=False)  # 100 is best


class StatisticMixin:
    '''
    This is used in Source sub-classes that are associated with statistics.
    '''

    def populate_statistics(self, session):
        cls = self.__class__
        cls_name = inspect(cls).tables[0].name
        cls_constraint_attr = cls.__statistic_constraint__
        cls_constraint = getattr(self, cls_constraint_attr)
        time_attr = cls.__statistic_time__
        time = getattr(self, time_attr)
        self.statistics = SimpleNamespace()
        for statistic in session.query(StatisticJournal).join(Statistic). \
                filter(Statistic.cls == cls_name, Statistic.cls_constraint == cls_constraint,
                       StatisticJournal.time == time).all():
            setattr(self.statistics, statistic.statistic.name, statistic)