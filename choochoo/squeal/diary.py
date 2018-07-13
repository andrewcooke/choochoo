
from sqlalchemy import Column, Integer, Text, Float

from .support import Base


class Diary(Base):

    __tablename__ = 'diary'

    ordinal = Column(Integer, primary_key=True)
    notes = Column(Text, nullable=False, default='')
    rest_hr = Column(Integer)
    sleep = Column(Float)
    mood = Column(Integer)
    weather = Column(Text, nullable=False, default='')
    medication = Column(Text, nullable=False, default='')
    weight = Column(Float)
