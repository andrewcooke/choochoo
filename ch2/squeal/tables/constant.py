
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .source import Source, SourceType
from ..support import Base


class Constant(Base):

    __tablename__ = 'constant'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)  # StatisticType
    statistic_id = Column(Integer, ForeignKey('statistic.id', ondelete='cascade'), nullable=False)
    statistic = relationship('Statistic')


class ConstantJournal(Source):

    __tablename__ = 'constant_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.CONSTANT
    }
