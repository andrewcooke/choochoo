from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, Text, ForeignKey, UniqueConstraint, Index, Float

from ..support import Base


class ClusterInputScratch(Base):

    __tablename__ = 'cluster_input_scratch'

    id = Column(Integer, primary_key=True)
    sector_group_id = Column(Integer, ForeignKey('sector_group.id', ondelete='cascade'), nullable=False)
    geom = Column(Geometry(geometry_type='GeometryM', dimension=3), nullable=False)  # some fragment of a route
    level = Column(Integer)
    group = Column(Integer)
    Index('natural_cluster_input_scratch_ix', 'sector_group_id', 'level', 'group')


class ClusterHull(Base):

    __tablename__ = 'cluster_hull'

    id = Column(Integer, primary_key=True)
    sector_group_id = Column(Integer, ForeignKey('sector_group.id', ondelete='cascade'), nullable=False)
    hull = Column(Geometry(), nullable=False)
    group = Column(Integer)
    level = Column(Integer)
    UniqueConstraint(sector_group_id, level, group)


class ClusterFragmentScratch(Base):

    __tablename__ = 'cluster_fragment_scratch'

    id = Column(Integer, primary_key=True)
    cluster_hull_id = Column(Integer, ForeignKey('cluster_hull.id', ondelete='cascade'), nullable=False, index=True)
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'), nullable=False, index=True)
    fragment = Column(Geometry('LineStringM'), nullable=False)
    length = Column(Float, nullable=False)
    Index('cluster_fragment_scratch_access_ix', cluster_hull_id, activity_journal_id, length)
