
from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from .source import Source, SourceType
from ..support import Base


class Constant(Source):

    __tablename__ = 'constant'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    statistic_journal_type = Column(Integer, nullable=False)
    # this could be the statistic_name or it could contain more info related to constraint
    name = Column(Text, nullable=False, index=True)
    statistic_name_id = Column(Integer, ForeignKey('statistic_name.id', ondelete='cascade'), nullable=False)
    statistic_name = relationship('StatisticName')

    __mapper_args__ = {
        'polymorphic_identity': SourceType.CONSTANT
    }

    def __str__(self):
        return 'Constant "%s"' % self.name


class SystemConstant(Base):

    __tablename__ = 'system_constant'

    name = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)


class InternPool(Base):

    __tablename__ = 'intern_pool'

    id = Column(Integer, primary_key=True)
    value = Column(Text, nullable=False, index=True)


INTERN_CACHE = {}


def intern(s, value):
    from ..database import add

    if value is None:
        return value

    # simplifying interning instances and classes
    if not isinstance(value, str) and not isinstance(value, type):
        value = type(value)
    if isinstance(value, type):
        value = value.__module__ + '.' + value.__name__

    if value not in INTERN_CACHE:
        intern = add(s, InternPool(value=value))
        s.flush()
        INTERN_CACHE[value] = intern.id
        INTERN_CACHE[intern.id] = value
    return INTERN_CACHE[value]


def unintern(s, id):

    if id is None:
        return id

    if id not in INTERN_CACHE:
        value = s.query(InternPool.value).filter(InternPool.id == id).scalar()
        INTERN_CACHE[value] = id
        INTERN_CACHE[id] = value
    return INTERN_CACHE[id]
