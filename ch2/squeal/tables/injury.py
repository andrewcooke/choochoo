
from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from .diary import BaseDiary
from ..support import Base
from ..types import Ordinal
from ...stoats.database import StatisticMixin


class Injury(Base):

    __tablename__ = 'injury'

    id = Column(Integer, primary_key=True)
    start = Column(Ordinal)
    finish = Column(Ordinal)
    name = Column(Text, nullable=False, server_default='', unique=True)
    description = Column(Text, nullable=False, server_default='')
    sort = Column(Text, nullable=False, server_default='')


class InjuryDiary(StatisticMixin, BaseDiary):

    __tablename__ = 'injury_diary'

    injury_id = Column(Integer, ForeignKey('injury.id'), primary_key=True)
    injury = relationship('Injury')
    # pain_average = Column(Integer)
    # pain_peak = Column(Integer)
    # pain_frequency = Column(Integer)
    notes = Column(Text, nullable=False, server_default='')

    __mapper_args__ = {
        'polymorphic_identity': 'activity',
    }
