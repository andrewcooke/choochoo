
from sqlalchemy import Column, Integer, Text, Float, UniqueConstraint

from ..types import Ordinal
from ..support import Base


class BaseDiary(Base):

    __tablename__ = 'base_diary'

    id = Column(Integer, primary_key=True)
    type = Column(Text)
    time = Column(Epoch)
    UniqueConstraint('type', 'time')

    __mapper_args__ = {
        'polymorphic_identity': 'diary',
        'polymorphic_on': type
    }


class DailyDiary(BaseDiary):

    __tablename__ = 'daily_diary'

    notes = Column(Text, nullable=False, server_default='')
    weather = Column(Text, nullable=False, server_default='')
    medication = Column(Text, nullable=False, server_default='')
    # rest_heart_rate = Column(Integer)
    # sleep = Column(Float)
    # mood = Column(Integer)
    # weight = Column(Float)

    __mapper_args__ = {
        'polymorphic_identity': 'daily',
    }
