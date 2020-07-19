
from enum import IntEnum
from json import dumps
from logging import getLogger

from sqlalchemy import Column, Integer, not_, or_, Table, ForeignKey
from sqlalchemy.orm import relationship, joinedload

from ..support import Base
from ..types import Cls, Json, Sort, short_cls

log = getLogger(__name__)


class PipelineType(IntEnum):

    READ_AND_CALCULATE = 0
    DISPLAY = 1
    DISPLAY_ACTIVITY = 2


PipelineDependency = Table('pipeline_dependency', Base.metadata,
                           Column('blocks', Integer, ForeignKey('pipeline.id'), primary_key=True),
                           Column('blocked_by', Integer, ForeignKey('pipeline.id'), primary_key=True))


class Pipeline(Base):

    __tablename__ = 'pipeline'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False, index=True)
    cls = Column(Cls, nullable=False)  # not unique - may run various instances
    kargs = Column(Json, nullable=False, server_default=dumps({}))
    sort = Column(Sort, nullable=False)

    # https://stackoverflow.com/a/5652169 (no idea why i need both here)
    blocks = relationship('Pipeline', secondary=PipelineDependency,
                          primaryjoin=PipelineDependency.c.blocked_by == id,
                          secondaryjoin=PipelineDependency.c.blocks == id,
                          back_populates='blocked_by')
    blocked_by = relationship('Pipeline', secondary=PipelineDependency,
                              primaryjoin=PipelineDependency.c.blocks == id,
                              secondaryjoin=PipelineDependency.c.blocked_by == id,
                              back_populates='blocks')

    @classmethod
    def _query(cls, s, type=None, like=tuple(), id=None):
        q = s.query(Pipeline)
        if type is not None:  # enum can be 0
            q = q.filter(Pipeline.type == type)
        if like:
            q = q.filter(or_(*[Pipeline.cls.like(pattern) for pattern in like]))
        if id:
            q = q.filter(Pipeline.id == id)
        return q

    @classmethod
    def all(cls, s, type, like=tuple(), id=None):
        q = cls._query(s, type, like=like, id=id)
        pipelines = q.order_by(Pipeline.sort).all()
        if not pipelines:
            msg = 'No pipelines configured for type %s' % PipelineType(type).name
            if like:
                msg += f' like {like}'
            if id:
                msg += f' with ID={id}'
            raise Exception(msg)
        return pipelines

    @classmethod
    def all_instances(cls, s, type, like=tuple(), id=None):
        for pipeline in cls.all(s, type, like=like, id=id):
            log.debug(f'Building {pipeline.cls} ({pipeline.kargs})')
            yield pipeline.cls(**pipeline.kargs)

    @classmethod
    def count(cls, s, type, like=tuple(), id=None):
        q = cls._query(s, type, like=like, id=id)
        return q.count()

    def __str__(self):
        return short_cls(self.cls)
