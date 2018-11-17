
from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from .source import Source, SourceType
from ..support import Base


class Constant(Source):

    __tablename__ = 'constant'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    statistic_journal_type = Column(Integer, nullable=False)
    # this could be the statistic_name or it could contain more info related to constraint
    name = Column(Text, nullable=False, index=True)
    statistic_name_id = Column(Integer, ForeignKey('statistic_name.id', ondelete='cascade'), nullable=False)
    statistic_name = relationship('StatisticName')

    __mapper_args__ = {
        'polymorphic_identity': SourceType.CONSTANT
    }

    def __str__(self):
        return 'Constant "%s"' % self.name


class SystemConstant(Base):

    __tablename__ = 'system_constant'

    name = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
