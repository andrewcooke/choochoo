
from json import dumps

from sqlalchemy import Column, Integer

from ..support import Base
from ..types import Cls, Json, Sort


class StatisticPipeline(Base):

    __tablename__ = 'statistic_pipeline'

    id = Column(Integer, primary_key=True)
    cls = Column(Cls, nullable=False)
    args = Column(Json, nullable=None, server_default=dumps(()))
    kargs = Column(Json, nullable=None, server_default=dumps({}))
    sort = Column(Sort)


class DiaryPipeline(Base):

    __tablename__ = 'diary_pipeline'

    id = Column(Integer, primary_key=True)
    cls = Column(Cls, nullable=False)
    args = Column(Json, nullable=None, server_default=dumps(()))
    kargs = Column(Json, nullable=None, server_default=dumps({}))
    sort = Column(Sort)
