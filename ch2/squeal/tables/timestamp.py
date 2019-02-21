
from contextlib import contextmanager
from time import time

from sqlalchemy import Column, Integer, UniqueConstraint, func

from ..types import Time, ShortCls, Str
from ..support import Base


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
    owner = Column(ShortCls, nullable=False)
    constraint = Column(Str)
    key = Column(Integer)
    UniqueConstraint(owner, constraint, key)

    @classmethod
    def set(cls, s, owner, constraint=None, key=None):
        cls.clear(s, owner, constraint=constraint, key=key)
        s.add(Timestamp(owner=owner, constraint=constraint, key=key))

    @classmethod
    def clear(cls, s, owner, constraint=None, key=None):
        exists = s.query(Timestamp). \
            filter(Timestamp.owner == owner,
                   Timestamp.constraint == constraint,
                   Timestamp.key == key).one_or_none()
        if exists:
            s.delete(exists)

    @contextmanager
    def on_success(self, s):
        self.clear(s, self.owner, constraint=self.constraint, key=self.key)
        yield None
        self.set(s, self.owner, constraint=self.constraint, key=self.key)
