
from contextlib import contextmanager
from logging import getLogger
from time import time

from sqlalchemy import Column, Integer, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.functions import count

from ..support import Base
from ..types import ShortCls, short_cls, NullText
from ...common.sql import Time

log = getLogger(__name__)


class Timestamp(Base):

    '''
    This was introduced to simplify tracking dependencies for statistics.

    For example, we only need to re-calculate summary statistics for data that are newer than the latest
    summary.

    Previously, dependencies were managed by complex logic (outer joins with missing values) that were
    hard to write and hard to understand later.  Also, they had the following problems:

    * Trying to re-calculate heart rate statistics when the "missing" values are caused by the activity
      having no HRM data.

    * Nearby activities being restricted to geographic regions, making it hard to decide if all relevant
      activities were included.
    '''

    __tablename__ = 'timestamp'

    id = Column(Integer, primary_key=True)
    time = Column(Time, nullable=False, default=time)
    owner = Column(ShortCls, nullable=False)  # index via unique
    constraint = Column(NullText)
    source_id = Column(Integer, ForeignKey('source.id', ondelete='cascade'))
    source = relationship('Source', foreign_keys=[source_id])
    UniqueConstraint(owner, constraint, source_id)

    @classmethod
    def set(cls, s, owner, constraint=None, source=None):
        cls.clear(s, owner, constraint=constraint, source=source)
        s.add(Timestamp(owner=owner, constraint=constraint, source=source))
        s.commit()
        log.debug(f'Timestamp for {short_cls(owner)} / {source}')

    @classmethod
    def get(cls, s, owner, constraint=None, source=None):
        return s.query(Timestamp). \
            filter(Timestamp.owner == owner,
                   Timestamp.constraint == constraint,
                   Timestamp.source == source).one_or_none()

    @classmethod
    def clear(cls, s, owner, constraint=None, source=None):
        s.query(Timestamp). \
            filter(Timestamp.owner == owner,
                   Timestamp.constraint == constraint,
                   Timestamp.source == source).delete()

    @classmethod
    def clear_keys(cls, s, source_ids, owner, constraint=None):
        s.commit()
        for repeat in range(2):
            q = s.query(Timestamp if repeat else count(Timestamp.id)). \
                filter(Timestamp.source_id.in_(source_ids),
                       Timestamp.owner == owner,
                       Timestamp.constraint == constraint)
            if repeat:
                q.delete(synchronize_session=False)
            else:
                log.debug(f'Clearing {q.scalar()} Timestamps for {short_cls(owner)} / {constraint}')    \

    @contextmanager
    def on_success(self, s):
        self.clear(s, self.owner, constraint=self.constraint, source=self.source)
        s.commit()
        yield None
        self.set(s, self.owner, constraint=self.constraint, source=self.source)

