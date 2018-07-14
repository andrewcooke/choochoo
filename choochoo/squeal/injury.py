
from sqlalchemy import Column, Integer, Text, ForeignKey

from .types import Ordinal
from .support import Base


class Injury(Base):

    __tablename__ = 'injury'

    id = Column(Integer, primary_key=True)
    start = Column(Ordinal)
    finish = Column(Ordinal)
    title = Column(Text, nullable=False, default='')
    description = Column(Text, nullable=False, default='')
    sort = Column(Text, nullable=False, default='')


class InjuryDiary(Base):

    __tablename__ = 'injury_diary'

    ordinal = Column(Ordinal, primary_key=True)
    injury_id = Column(Integer, ForeignKey('injury.id'), primary_key=True)
    pain_average = Column(Integer)
    pain_peak = Column(Integer)
    pain_frequency = Column(Integer)
    notes = Column(Text, nullable=False, default='')
