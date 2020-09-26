from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, Text, ForeignKey, UniqueConstraint, Index

from ..support import Base


class ClusterTmp(Base):

    __tablename__ = 'cluster_tmp'

    id = Column(Integer, primary_key=True)
    statistic_id = Column(Integer, ForeignKey('statistic_journal.id', ondelete='cascade'), nullable=False, index=True)
    point = Column(Geometry('Point'), nullable=False)
    tag = Column(Text, nullable=False)
    group = Column(Integer)
    level = Column(Integer)
    Index('natural_cluster_ix', 'tag', 'level', 'group')


class Cluster(Base):

    __tablename__ = 'cluster'

    id = Column(Integer, primary_key=True)
    hull = Column(Geometry(), nullable=False)
    tag = Column(Text, index=True, nullable=False)
    group = Column(Integer)
    level = Column(Integer)
    UniqueConstraint(tag, level, group)
