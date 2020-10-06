from logging import getLogger

from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, Float, UniqueConstraint, or_
from sqlalchemy.orm import relationship

from .source import GroupedSource, Source, SourceType
from ..support import Base
from ..triggers import add_child_ddl
from ..types import ShortCls, Point
from ..utils import add
from ...common.geo import utm_srid

log = getLogger(__name__)


@add_child_ddl(Source)
class SectorJournal(GroupedSource):

    __tablename__ = 'sector_journal'

    id = Column(Integer, ForeignKey('source.id', ondelete='cascade'), primary_key=True)
    # do not use on delete cascade here since it leaves source entries without children
    # instead, to guarantee consistency, call clean()
    sector_id = Column(Integer, ForeignKey('sector.id', ondelete='set null'), index=True)
    sector = relationship('Sector')
    # do not use on delete cascade here since it leaves source entries without children
    # instead, to guarantee consistency, call clean()
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='set null'),
                                 index=True)
    activity_journal = relationship('ActivityJournal', foreign_keys=[activity_journal_id])
    # these duplicate data (can be extracted from st_linesubstring and the activity route)
    # but simplify time_range below.
    start = Column(DateTime(timezone=True), nullable=False)
    finish = Column(DateTime(timezone=True), nullable=False)
    start_fraction = Column(Float, nullable=False)
    finish_fraction = Column(Float, nullable=False)
    UniqueConstraint(sector_id, activity_journal_id, start_fraction, finish_fraction)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.SECTOR
    }

    def time_range(self, s):
        return self.start, self.finish

    @classmethod
    def clean(cls, s):
        q1 = s.query(SectorJournal.id). \
            filter(or_(SectorJournal.segment_id == None,
                       SectorJournal.activity_journal_id == None)).cte()
        s.query(Source).filter(Source.id.in_(q1)).delete(synchronize_session=False)


class SectorGroup(Base):

    __tablename__ = 'sector_group'

    id = Column(Integer, primary_key=True)
    srid = Column(Integer, nullable=False)
    centre = Column(Point, nullable=False)
    radius = Column(Float, nullable=False)  # metres
    title = Column(Text, nullable=False)
    UniqueConstraint(centre, radius, title)

    @classmethod
    def add(cls, s, lat, lon, radius_km, title):
        srid = utm_srid(lat, lon)
        add(s, SectorGroup(srid=srid, centre=(lon, lat), radius=radius_km * 1000, title=title))


class Sector(Base):

    __tablename__ = 'sector'

    id = Column(Integer, primary_key=True)
    sector_group_id = Column(Integer, ForeignKey('activity_journal.id', ondelete='cascade'), nullable=False)
    route = Column(Geometry('LineString'), nullable=False)
    title = Column(Text, nullable=False)
    owner = Column(ShortCls, nullable=False, index=True)
