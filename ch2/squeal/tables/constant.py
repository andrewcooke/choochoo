
from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from .statistic import Statistic, StatisticJournal
from .source import Source, SourceType
from ..support import Base


class Constant(Base):

    __tablename__ = 'constant'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)  # StatisticType
    name = Column(Text, nullable=False)
    statistic_id = Column(Integer, ForeignKey('statistic.id', ondelete='cascade'), nullable=False)
    statistic = relationship('Statistic')


class ConstantJournal(Source):

    __tablename__ = 'constant_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)

    @staticmethod
    def lookup_statistic_journal(log, s, name, constraint, time):
        # order important in join here
        # todo - what is join with constant for?  using source as constraint?  should be owner
        # todo - does it even work?
        return s.query(StatisticJournal).join(ConstantJournal, Statistic, Constant). \
            filter(Statistic.constraint == constraint,
                   Statistic.name == name,
                   ConstantJournal.time <= time).one_or_none()

    __mapper_args__ = {
        'polymorphic_identity': SourceType.CONSTANT
    }


class SystemConstant(Base):

    __tablename__ = 'system_constant'

    name = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
