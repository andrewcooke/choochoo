
from enum import IntEnum
from json import dumps
from logging import getLogger

from sqlalchemy import Column, Integer, not_, or_, Table, ForeignKey, Text
from sqlalchemy.orm import relationship, joinedload

from ..support import Base
from ..types import Cls, Json, Sort, short_cls

log = getLogger(__name__)


class PipelineType(IntEnum):

    PROCESS = 0
    DISPLAY = 1
    DISPLAY_ACTIVITY = 2


# todo - possibly this should be expressed as a dependency on services, rather than directly between pipelines.
# (i tried this, getting as far as sketching out the tables, and it seemed like a lot of complexity for not
# much gain when the configuration is not varied much - might be more useful in future with a more flexible
# system).

# purely for joins, so not exposed by sqlalchemy
PipelineDependency = Table('pipeline_dependency', Base.metadata,
                           Column('blocks', Integer, ForeignKey('pipeline.id'), primary_key=True),
                           Column('blocked_by', Integer, ForeignKey('pipeline.id'), primary_key=True))


class Pipeline(Base):

    __tablename__ = 'pipeline'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False, index=True)
    cls = Column(Cls, nullable=False)  # not unique - may run various instances
    kargs = Column(Json, nullable=False, server_default=dumps({}))

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
        pipelines = cls._query(s, type, like=like, id=id).all()
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
        for pipeline in sort_pipelines(cls.all(s, type, like=like, id=id)):
            log.debug(f'Building {pipeline.cls} ({pipeline.kargs})')
            yield pipeline.cls(**pipeline.kargs)

    @classmethod
    def count(cls, s, type, like=tuple(), id=None):
        q = cls._query(s, type, like=like, id=id)
        return q.count()

    def __str__(self):
        return short_cls(self.cls)


def sort_pipelines(pipelines):
    '''
    not only does this order pipelines so that, if run in order, none is blocked.  it also expands the
    graph so that when the session is disconnected we have all the data we need.
    '''
    included, processed, remaining = set(pipelines), set(), set(pipelines)
    log.debug(f'Sorting {", ".join(str(pipeline) for pipeline in included)}')
    while remaining:
        for pipeline in remaining:
            if all(blocker not in included or blocker in processed for blocker in pipeline.blocked_by):
                yield pipeline
                processed.add(pipeline)
        remaining = remaining.difference(processed)
