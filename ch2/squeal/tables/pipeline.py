
from enum import IntEnum
from json import dumps

from sqlalchemy import Column, Integer

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
    args = Column(Json, nullable=None, server_default=dumps(()))
    kargs = Column(Json, nullable=None, server_default=dumps({}))
    sort = Column(Sort)

    @classmethod
    def all(cls, log, s, type, like=None):
        q = s.query(Pipeline).filter(Pipeline.type == type)
        if like:
            q = q.filter(Pipeline.cls.like(like))
        pipelines = q.order_by(Pipeline.sort).all()
        if not pipelines:
            msg = 'No pipelines configured for type %s' % PipelineType(type).name
            if like:
                msg += (' like %' % like)
            raise Exception(msg)
        yield from ((pipeline.cls, pipeline.args, pipeline.kargs) for pipeline in pipelines)
