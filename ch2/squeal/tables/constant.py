
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .statistic import Statistic, StatisticJournal
from .source import Source, SourceType
from ..support import Base


class Constant(Base):

    __tablename__ = 'constant'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)  # StatisticType
    statistic_id = Column(Integer, ForeignKey('statistic.id', ondelete='cascade'), nullable=False)
    statistic = relationship('Statistic')

    @staticmethod
    def lookup(log, s, name):
        constant = s.query(Constant).join(Statistic). \
            filter(Statistic.name == name,
                   Statistic.owner == Constant).one_or_none()
        if not constant:
            constants = s.query(Constant).all()
            if constants:
                log.info('Available constants:')
                for constant in constants:
                    log.info('%s - %s' % (constant.statistic.name, constant.statistic.description))
            else:
                log.error('No constants defined - configure system correctly')
            raise Exception('Constant "%s" is not defined' % name)
        return constant


class ConstantJournal(Source):

    __tablename__ = 'constant_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)

    @staticmethod
    def lookup(log, s, name, time):
        constant = Constant.lookup(log, s, name)
        return s.query(StatisticJournal).join(ConstantJournal). \
            filter(StatisticJournal.statistic == constant.statistic,
                   ConstantJournal.time <= time).one_or_none()

    __mapper_args__ = {
        'polymorphic_identity': SourceType.CONSTANT
    }
