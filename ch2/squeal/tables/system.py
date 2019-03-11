from time import time

from sqlalchemy import Column, Text, Integer

from ..support import Base
from ..types import Time, ShortCls


class SystemConstant(Base):

    __tablename__ = 'system_constant'

    name = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)

    TIMEZONE = 'timezone'


class SystemProcess(Base):

    __tablename__ = 'system_process'

    id = Column(Integer, primary_key=True)
    command = Column(Text, nullable=False)
    log = Column(Text, nullable=False)
    start = Column(Time, nullable=False, default=time)
    owner = Column(ShortCls, nullable=False, index=True)
    pid = Column(Integer, nullable=False, index=True)
