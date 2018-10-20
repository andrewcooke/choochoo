
from sqlalchemy import Column, Text, Integer, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from .source import Source, SourceType
from ..support import Base
from ..types import Time, Sort


class MonitorJournal(Source):

    __tablename__ = 'monitor_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    fit_file = Column(Text, nullable=False, unique=True)
    finish = Column(Time, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.MONITOR
    }

    def __str__(self):
        return 'Monitor Journal from %s' % self.time


class MonitorIntegerMixin:

    id = Column(Integer, primary_key=True)
    time = Column(Time, nullable=False)
    value = Column(Integer, nullable=False)
    UniqueConstraint('monitor_journal_id', 'time')


class MonitorHeartRate(MonitorIntegerMixin, Base):

    __tablename__ = 'monitor_heart_rate'

    monitor_journal_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'),
                                nullable=False)
    monitor_journal = relationship('MonitorJournal',
                                   backref=backref('heart_rate', cascade='all, delete-orphan',
                                                   passive_deletes=True,
                                                   order_by='MonitorHeartRate.time'))


class MonitorSteps(MonitorIntegerMixin, Base):

    __tablename__ = 'monitor_steps'

    monitor_journal_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'),
                                nullable=False)
    monitor_journal = relationship('MonitorJournal',
                                   backref=backref('steps', cascade='all, delete-orphan',
                                                   passive_deletes=True,
                                                   order_by='MonitorSteps.time'))
