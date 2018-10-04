
from enum import Enum, IntEnum
from types import SimpleNamespace

from sqlalchemy import Column, Integer, ForeignKey, Text, UniqueConstraint, Float, inspect
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, backref

from ..support import Base
from ..types import Cls
from ...lib.date import format_duration


class Statistic(Base):

    __tablename__ = 'statistic'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)  # simple, displayable name
    description = Column(Text)
    units = Column(Text)
    summary = Column(Text)  # '[max]', '[min]' etc - can be multiple values but each in square brackets
    # we need to disambiguate statistics with the same name.
    # this is done by (1) "owner" (typically the source of the data) and
    # (2) by some additional (optional) constraint used by the owner (typically)
    # (eg activity.id so that the same statistic can be used across different activities)
    owner = Column(Cls, nullable=False)
    constraint = Column(Integer)

    def __str__(self):
        return 'Statistic "%s"' % self.name


class StatisticType(IntEnum):

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

    def __str__(self):
        try:
            return 'StatisticJournal "%s"' % self.value
        except AttributeError:
            return 'Base Journal'

    @property
    def time(self):
        return self.source.time

    @classmethod
    def add(cls, log, s, name, units, summary, owner, constraint, source, value, type):
        statistic = s.query(Statistic). \
            filter(Statistic.name == name,
                   Statistic.owner == owner,
                   Statistic.constraint == constraint).one_or_none()
        if not statistic:
            statistic = Statistic(name=name, units=units, summary=summary, owner=owner, constraint=constraint)
            s.add(statistic)
        else:
            if statistic.units != units:
                log.warn('Changing units on %s (%s -> %s)' % (statistic.name, statistic.units, units))
                statistic.units = units
            if statistic.summary != summary:
                log.warn('Changing summary on %s (%s -> %s)' % (statistic.name, statistic.summary, summary))
                statistic.summary = summary
        journal = s.query(StatisticJournal). \
            filter(StatisticJournal.statistic == statistic,
                   StatisticJournal.source == source).one_or_none()
        if not journal:
            journal = STATISTIC_JOURNAL_CLASSES[type](
                statistic=statistic, source=source, value=value)
            s.add(journal)
        else:
            if journal.type != type:
                raise Exception('Inconsistent StatisticJournal type (%d != %d)' %
                                (journal.type, journal))
            journal.value = value
        return journal


class StatisticJournalInteger(StatisticJournal):

    __tablename__ = 'statistic_journal_integer'

    id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), primary_key=True)
    value = Column(Integer)

    parse = int

    __mapper_args__ = {
        'polymorphic_identity': StatisticType.INTEGER
    }

    @classmethod
    def add(cls, log, s, name, units, summary, owner, constraint, source, value):
        return super().add(log, s, name, units, summary, owner, constraint, source, value, StatisticType.INTEGER)

    # def formatted(self):
    #     units = self.statistic.units
    #     if not units:
    #         return '%d' % self.value
    #     elif units == 'm':
    #         if self.value > 2000:
    #             return '%dkm' % (self.value / 1000)
    #         else:
    #             return '%dm' % self.value
    #     elif units == 's':
    #         return format_duration(self.value)
    #     elif units == 'km/h':
    #         return '%dkm/h' % self.value
    #     elif units == '%':
    #         return '%d%%' % self.value
    #     elif units == 'bpm':
    #         return '%dbpm' % self.value
    #     else:
    #         return '%d%s' % (self.value, units)


class StatisticJournalFloat(StatisticJournal):

    __tablename__ = 'statistic_journal_float'

    id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), primary_key=True)
    value = Column(Float)

    parse = float

    @classmethod
    def add(cls, log, s, name, units, summary, owner, constraint, source, value):
        return super().add(log, s, name, units, summary, owner, constraint, source, value, StatisticType.FLOAT)

    __mapper_args__ = {
        'polymorphic_identity': StatisticType.FLOAT
    }

    # def formatted(self):
    #     units = self.statistic.units
    #     if not units:
    #         return '%f' % self.value
    #     elif units == 'm':
    #         if self.value > 2000:
    #             return '%.1fkm' % (self.value / 1000)
    #         else:
    #             return '%dm' % int(self.value)
    #     elif units == 's':
    #         return format_duration(self.value)
    #     elif units == 'km/h':
    #         return '%.1fkm/h' % self.value
    #     elif units == '%':
    #         return '%.1f%%' % self.value
    #     elif units == 'bpm':
    #         return '%dbpm' % int(self.value)
    #     else:
    #         return '%s%s' % (self.value, units)


class StatisticJournalText(StatisticJournal):

    __tablename__ = 'statistic_journal_text'

    id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), primary_key=True)
    value = Column(Text)

    parse = str

    @classmethod
    def add(cls, log, s, name, units, summary, owner, constraint, source, value):
        return super().add(log, s, name, units, summary, owner, constraint, source, value, StatisticType.TEXT)

    __mapper_args__ = {
        'polymorphic_identity': StatisticType.TEXT
    }

    # def formatted(self):
    #     if not self.units:
    #         return '%s' % self.value
    #     else:
    #         return '%s%s' % (self.value, self.units)


class StatisticMeasure(Base):

    __tablename__ = 'statistic_rank'

    id = Column(Integer, primary_key=True)
    statistic_journal_id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), nullable=False)
    statistic_journal = relationship('StatisticJournal',
                                     backref=backref('measures', cascade='all, delete-orphan',
                                                     passive_deletes=True,
                                                     order_by='desc(StatisticMeasure.rank)'))
    source_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), nullable=False)  # must be an interval
    source = relationship('Source')
    rank = Column(Integer, nullable=False)  # 1 is best
    percentile = Column(Float, nullable=False)  # 100 is best


STATISTIC_JOURNAL_CLASSES = {
    StatisticType.INTEGER: StatisticJournalInteger,
    StatisticType.FLOAT: StatisticJournalFloat,
    StatisticType.TEXT: StatisticJournalText
}


class StatisticPipeline(Base):

    __tablename__ = 'statistic_pipeline'

    id = Column(Integer, primary_key=True)
    cls = Column(Cls, nullable=False)
    sort = Column(Integer)

