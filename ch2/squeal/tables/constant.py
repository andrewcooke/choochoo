
from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from .statistic import StatisticName, StatisticJournal
from .source import Source, SourceType
from ..support import Base


class Constant(Base):

    __tablename__ = 'constant'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)  # StatisticJournalType
    name = Column(Text, nullable=False)
    statistic_name_id = Column(Integer, ForeignKey('statistic_name.id', ondelete='cascade'), nullable=False)
    statistic_name = relationship('StatisticName')


class ConstantJournal(Source):

    __tablename__ = 'constant_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)

    @staticmethod
    def lookup_statistic_journal(log, s, name, constraint, time):
        # order important in join here
        return s.query(StatisticJournal).join(ConstantJournal, StatisticName, Constant). \
            filter(StatisticName.constraint == constraint,
                   StatisticName.name == name,
                   ConstantJournal.time <= time).one_or_none()

    __mapper_args__ = {
        'polymorphic_identity': SourceType.CONSTANT
    }


class SystemConstant(Base):

    __tablename__ = 'system_constant'

    name = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
