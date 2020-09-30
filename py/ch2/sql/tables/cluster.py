from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, Text, ForeignKey, UniqueConstraint, Index, Float

from ..support import Base


class ClusterParameters(Base):

    __tablename__ = 'cluster_parameters'
    id = Column(Integer, primary_key=True)
    srid = Column(Integer, nullable=False)
    centre = Column(Geometry('Point'), nullable=False)
    radius = Column(Float, nullable=False)
    note = Column(Text, nullable=False)
    UniqueConstraint(srid, centre, radius, note)


class ClusterInputScratch(Base):

    __tablename__ = 'cluster_input_scratch'

    id = Column(Integer, primary_key=True)
    cluster_parameters_id = Column(Integer, ForeignKey('cluster_parameters.id', ondelete='cascade'), nullable=False)
    geom = Column(Geometry(), nullable=False)  # some fragment of a route
    level = Column(Integer)
    group = Column(Integer)
    Index('natural_cluster_input_scratch_ix', 'parameters', 'level', 'group')


class ClusterHull(Base):

    __tablename__ = 'cluster_hull'

    id = Column(Integer, primary_key=True)
    cluster_parameters_id = Column(Integer, ForeignKey('cluster_parameters.id', ondelete='cascade'), nullable=False)
    hull = Column(Geometry(), nullable=False)
    group = Column(Integer)
    level = Column(Integer)
    UniqueConstraint(cluster_parameters_id, level, group)


class ClusterFragmentScratch(Base):

    __tablename__ = 'cluster_fragment_scratch'

    id = Column(Integer, primary_key=True)
    cluster_hull_id = Column(Integer, ForeignKey('cluster_hull.id', ondelete='cascade'), nullable=False)
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'), nullable=False)
    fragment = Column(Geometry('LineString'), nullable=False)
    length = Column(Float, nullable=False)


class ClusterArchetype(Base):

    __tablename__ = 'cluster_archetype'

    id = Column(Integer, primary_key=True)
    cluster_hull_id = Column(Integer, ForeignKey('cluster_hull.id', ondelete='cascade'), nullable=False)
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'), nullable=False)
    fragment = Column(Geometry('LineString'), nullable=False)
    length = Column(Float, nullable=False)


class ClusterMember(Base):

    __tablename__ = 'cluster_member'

    id = Column(Integer, primary_key=True)
    cluster_archetype_id = Column(Integer, ForeignKey('cluster_archetype.id', ondelete='cascade'), nullable=False)
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'), nullable=False)
    fragment = Column(Geometry('LineString'), nullable=False)
    # todo - maybe duration?  offsets into activity?
