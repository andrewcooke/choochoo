
import datetime as dt
from enum import IntEnum

from sqlalchemy import Column, Integer, ForeignKey, Text, UniqueConstraint, Float, desc, asc, Index
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, backref

from .source import Interval
from ..support import Base
from ..types import Time, ShortCls, NullStr
from ..utils import add
from ...lib.date import format_seconds, local_date_to_time
from ...lib.utils import sigfig
from ...stoats.names import KMH, PC, BPM, STEPS_UNITS, S, M, KG, W, KCAL, KJ


class StatisticName(Base):

    __tablename__ = 'statistic_name'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, index=True)  # simple, displayable name
    description = Column(Text)
    units = Column(Text)
    summary = Column(Text)  # '[max]', '[min]' etc - can be multiple values but each in square brackets
    # we need to disambiguate statistics with the same name.
    # this is done by (1) "owner" (typically the source of the data) and
    # (2) by some additional (optional) constraint used by the owner (typically)
    # (eg activity_group.id so that the same statistic can be used across different activities)
    owner = Column(ShortCls, nullable=False, index=True)  # index for deletion
    constraint = Column(NullStr)
    statistic_journal_type = Column(Integer, nullable=False)  # StatisticJournalType
    UniqueConstraint(name, owner, constraint)

    def __str__(self):
        return '"%s" (%s/%s)' % (self.name, self.owner, self.constraint)

    @classmethod
    def add_if_missing(cls, log, s, name, type, units, summary, owner, constraint):
        s.commit()  # start new transaction here in case rollback
        q = s.query(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticName.owner == owner,
                   StatisticName.constraint == constraint)
        statistic_name = q.one_or_none()
        if not statistic_name:
            statistic_name = add(s, StatisticName(name=name, units=units, summary=summary, owner=owner,
                                                  constraint=constraint, statistic_journal_type=type))
            try:
                s.flush()
            except IntegrityError as e:  # worker may have created in parallel, so read
                log.debug(f'Rollback for {e}')
                s.rollback()
                log.debug('Now trying retrieval...')
                statistic_name = q.one()
                log.debug('Retrieved')
        else:
            if statistic_name.statistic_journal_type != type:
                raise Exception('Changing type on %s (%s -> %s)' %
                                (statistic_name.name, statistic_name.statistic_journal_type, type))
            if statistic_name.units != units:
                log.warning('Changing units on %s (%s -> %s)' % (statistic_name.name, statistic_name.units, units))
                statistic_name.units = units
                s.flush()
            if statistic_name.summary != summary:
                log.warning('Changing summary on %s (%s -> %s)' % (statistic_name.name, statistic_name.summary, summary))
                statistic_name.summary = summary
                s.flush()
        return statistic_name

    @classmethod
    def parse(cls, name, default_owner=None, default_constraint=None):
        parts, owner, constraint = name.split(':'), None, None
        if len(parts) == 1:
            name = parts[0]
        elif len(parts) == 2:
            owner, name = parts
        else:
            owner, name, constraint = parts
        if not owner: owner = default_owner
        if not owner:
            raise Exception(f'Missing owner for {name}')
        if not constraint: constraint = default_constraint
        return owner, name, constraint


class StatisticJournalType(IntEnum):

    STATISTIC = 0
    INTEGER = 1
    FLOAT = 2
    TEXT = 3


class StatisticJournal(Base):

    __tablename__ = 'statistic_journal'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False, index=True)  # index needed for fast delete of subtypes
    statistic_name_id = Column(Integer, ForeignKey('statistic_name.id', ondelete='cascade'),
                               nullable=False, index=True)
    statistic_name = relationship('StatisticName')
    source_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'),
                       nullable=False, index=True)
    source = relationship('Source')
    time = Column(Time, nullable=False)
    # serial "counts" along values in the timeseries.  it's optional.  for garmin, all values appear each
    # record, so all imported values share the same serial.  but that's not true for the corrected elevation,
    # for example.
    serial = Column(Integer)
    UniqueConstraint(statistic_name_id, time)
    UniqueConstraint(serial, source_id, statistic_name_id)
    Index('from_activity_timespan', source_id, statistic_name_id, time)  # time last since inequality

    __mapper_args__ = {
        'polymorphic_identity': StatisticJournalType.STATISTIC,
        'polymorphic_on': 'type'
    }

    def __str__(self):
        try:
            return 'StatisticJournal "%s"' % self.value
        except AttributeError:
            return 'Field Journal'

    @classmethod
    def add(cls, log, s, name, units, summary, owner, constraint, source, value, time, serial, type):
        statistic_name = StatisticName.add_if_missing(log, s, name, type, units, summary, owner, constraint)
        journal = STATISTIC_JOURNAL_CLASSES[type](
                statistic_name=statistic_name, source=source, value=value, time=time, serial=serial)
        s.add(journal)
        return journal

    def formatted(self):
        if self.value is None:
            return None
        units = self.statistic_name.units
        if not units:
            return '%d' % self.value
        elif units == M:
            if self.value > 2000:
                return '%d km' % (self.value / 1000)
            else:
                return '%d m' % self.value
        elif units == S:
            return format_seconds(self.value)
        elif units in (KMH, PC, BPM, STEPS_UNITS, W, KJ):
            return '%d %s' % (self.value, units)
        elif units == KCAL:
            return '%s %s' % (sigfig(self.value, 2), units)
        else:
            return '%d %s' % (self.value, units)

    def measures_as_text(self, date):
        words = []
        if hasattr(self, 'measures'):
            for measure in sorted(self.measures,
                                  key=lambda measure: measure.source.schedule.frame_length_in_days(date)):
                if words:
                    words += [',']
                quintile = 1 + min(4, measure.percentile / 20)
                words += [('quintile-%d' % quintile, '%d%%' % int(measure.percentile))]
                if measure.rank < 5:
                    words += [':', ('rank-%d' % measure.rank, '%d' % measure.rank)]
                words += ['/' + measure.source.schedule.describe(compact=True)]
        return words

    @classmethod
    def at_date(cls, s, date, name, owner, constraint, source_id=None):
        start = local_date_to_time(date)
        finish = start + dt.timedelta(days=1)
        q = s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticJournal.time >= start,
                   StatisticJournal.time < finish,
                   StatisticName.owner == owner,
                   StatisticName.constraint == constraint)
        if source_id is not None:
            q = q.filter(StatisticJournal.source_id == source_id)
        return q.one_or_none()

    @classmethod
    def at(cls, s, time, name, owner, constraint):
        return s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticJournal.time == time,
                   StatisticName.owner == owner,
                   StatisticName.constraint == constraint).one_or_none()

    @classmethod
    def before(cls, s, time, name, owner, constraint):
        return s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticJournal.time <= time,
                   StatisticName.owner == owner,
                   StatisticName.constraint == constraint). \
            order_by(desc(StatisticJournal.time)).limit(1).one_or_none()

    @classmethod
    def after(cls, s, time, name, owner, constraint):
        return s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticJournal.time >= time,
                   StatisticName.owner == owner,
                   StatisticName.constraint == constraint). \
            order_by(asc(StatisticJournal.time)).limit(1).one_or_none()

    @classmethod
    def at_interval(cls, s, start, schedule, statistic_owner, statistic_constraint, interval_owner):
        return s.query(StatisticJournal).join(StatisticName, Interval). \
                    filter(StatisticJournal.statistic_name_id == StatisticName.id,
                           Interval.schedule == schedule,
                           Interval.start == start,
                           Interval.owner == interval_owner,
                           StatisticName.owner == statistic_owner,
                           StatisticName.constraint == statistic_constraint). \
                    order_by(StatisticName.constraint,  # order places summary stats from same source together
                             StatisticName.name).all()

    @classmethod
    def for_source(cls, s, source_id, name, owner, constraint):
        return s.query(StatisticJournal).join(StatisticName). \
            filter(StatisticName.name == name,
                   StatisticName.owner == owner,
                   StatisticName.constraint == constraint,
                   StatisticJournal.source_id == source_id).one_or_none()


class StatisticJournalInteger(StatisticJournal):

    __tablename__ = 'statistic_journal_integer'

    id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), primary_key=True)
    value = Column(Integer)
    # Index('cover_integer', id, value)  # experiment with covering index

    parse = int

    __mapper_args__ = {
        'polymorphic_identity': StatisticJournalType.INTEGER
    }

    @classmethod
    def add(cls, log, s, name, units, summary, owner, constraint, source, value, time, serial=None):
        return super().add(log, s, name, units, summary, owner, constraint, source, value, time, serial,
                           StatisticJournalType.INTEGER)


class StatisticJournalFloat(StatisticJournal):

    __tablename__ = 'statistic_journal_float'

    id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), primary_key=True)
    value = Column(Float)
    # Index('cover_float', id, value)

    parse = float

    @classmethod
    def add(cls, log, s, name, units, summary, owner, constraint, source, value, time, serial=None):
        return super().add(log, s, name, units, summary, owner, constraint, source, value, time, serial,
                           StatisticJournalType.FLOAT)

    __mapper_args__ = {
        'polymorphic_identity': StatisticJournalType.FLOAT
    }

    def formatted(self):
        if self.value is None:
            return None
        units = self.statistic_name.units
        if not units:
            return '%f' % self.value
        elif units == M:
            if self.value > 2000:
                return '%.1f km' % (self.value / 1000)
            else:
                return '%d m' % int(self.value)
        elif units == S:
            return format_seconds(self.value)
        elif units in (KMH, PC, KG, W, KJ):
            return '%.1f %s' % (self.value, units)
        elif units == KCAL:
            return '%s %s' % (sigfig(self.value, 2), units)
        elif units in (BPM, STEPS_UNITS):
            return '%d %s' % (int(self.value), units)
        else:
            return '%s %s' % (self.value, units)


class StatisticJournalText(StatisticJournal):

    __tablename__ = 'statistic_journal_text'

    id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), primary_key=True)
    value = Column(Text)
    # Index('cover_text', id, value)

    parse = str

    @classmethod
    def add(cls, log, s, name, units, summary, owner, constraint, source, value, time, serial=None):
        return super().add(log, s, name, units, summary, owner, constraint, source, value, time, serial,
                           StatisticJournalType.TEXT)

    __mapper_args__ = {
        'polymorphic_identity': StatisticJournalType.TEXT
    }

    def formatted(self):
        if self.value is None:
            return None
        if not self.units:
            return '%s' % self.value
        else:
            return '%s %s' % (self.value, self.units)


class StatisticMeasure(Base):

    __tablename__ = 'statistic_measure'

    id = Column(Integer, primary_key=True)
    statistic_journal_id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'),
                                  nullable=False, index=True)
    statistic_journal = relationship('StatisticJournal',
                                     backref=backref('measures', cascade='all, delete-orphan',
                                                     passive_deletes=True,
                                                     order_by='desc(StatisticMeasure.rank)'))
    source_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'),
                       nullable=False, index=True)  # must be an interval
    source = relationship('Source')
    rank = Column(Integer, nullable=False)  # 1 is best [1..n]
    percentile = Column(Float, nullable=False)  # 100 is best [0..100]
    quartile = Column(Integer)  # 0..4 at the min, 25%, median, 75% and max points


STATISTIC_JOURNAL_CLASSES = {
    StatisticJournalType.INTEGER: StatisticJournalInteger,
    StatisticJournalType.FLOAT: StatisticJournalFloat,
    StatisticJournalType.TEXT: StatisticJournalText
}

STATISTIC_JOURNAL_TYPES = {
    StatisticJournalInteger: StatisticJournalType.INTEGER,
    StatisticJournalFloat: StatisticJournalType.FLOAT,
    StatisticJournalText: StatisticJournalType.TEXT
}

TYPE_TO_JOURNAL_CLASS = {
    int: StatisticJournalInteger,
    float: StatisticJournalFloat,
    str: StatisticJournalText
}

