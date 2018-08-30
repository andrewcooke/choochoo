
from sqlalchemy import Column, Integer, Text, Float

from ..types import Ordinal
from ..support import Base


class Diary(Base):

    __tablename__ = 'diary'

    date = Column(Ordinal, primary_key=True)
    notes = Column(Text, nullable=False, server_default='')
    rest_hr = Column(Integer)
    sleep = Column(Float)
    mood = Column(Integer)
    weather = Column(Text, nullable=False, server_default='')
    medication = Column(Text, nullable=False, server_default='')
    weight = Column(Float)
