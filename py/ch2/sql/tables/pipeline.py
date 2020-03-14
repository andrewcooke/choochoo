
from enum import IntEnum
from json import dumps

from sqlalchemy import Column, Integer, not_

from ..support import Base
from ..types import Cls, Json, Sort


class PipelineType(IntEnum):

    STATISTIC = 0
    DIARY = 1
    ACTIVITY = 2
    MONITOR = 3


class Pipeline(Base):

    __tablename__ = 'pipeline'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False)
    cls = Column(Cls, nullable=False)
    args = Column(Json, nullable=False, server_default=dumps(()))
    kargs = Column(Json, nullable=False, server_default=dumps({}))
    sort = Column(Sort, nullable=False)

    @classmethod
    def all(cls, s, type, like=tuple(), unlike=tuple(), id=None):
        q = s.query(Pipeline).filter(Pipeline.type == type)
        for pattern in like:
            q = q.filter(Pipeline.cls.like(pattern))
        for pattern in unlike:
            q = q.filter(not_(Pipeline.cls.like(pattern)))
        if id:
            q = q.filter(Pipeline.id == id)
        pipelines = q.order_by(Pipeline.sort).all()
        if not pipelines:
            msg = 'No pipelines configured for type %s' % PipelineType(type).name
            if like:
                msg += f' like {like}'
            if id:
                msg += f' with ID={id}'
            raise Exception(msg)
        yield from pipelines
