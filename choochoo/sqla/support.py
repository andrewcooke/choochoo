
from functools import total_ordering

from sqlalchemy import Column, Text
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


@total_ordering
class SortMixin:

    sort = Column(Text, nullable=False, default='')

    def __lt__(self, other):
        return self.sort < other.sort
