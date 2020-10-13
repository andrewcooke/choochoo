from enum import IntEnum
from logging import getLogger

from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, Text, ForeignKey, Float, UniqueConstraint, or_
from sqlalchemy.orm import relationship

from .source import GroupedSource, Source, SourceType
from .statistic import StatisticJournalType
from ..support import Base
from ..triggers import add_child_ddl, add_text
from ..types import ShortCls, Point, UTC
from ..utils import add
from ...common.geo import utm_srid
from ...names import N, T, U, S

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
    start = Column(UTC, nullable=False)
    finish = Column(UTC, nullable=False)
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


class SectorType(IntEnum):

    SECTOR = 0
    CLIMB = 1


@add_text('''
alter table sector
  add constraint sector_optional_exclusion
  exclude using gist (owner with =,
                      sector_group_id with =,
                      exclusion with &&)
''')
class Sector(Base):

    __tablename__ = 'sector'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False, index=True)  # index needed for fast delete of subtypes
    sector_group_id = Column(Integer, ForeignKey('sector_group.id', ondelete='cascade'), nullable=False)
    sector_group = relationship('SectorGroup')
    route = Column(Geometry('LineString'), nullable=False)
    distance = Column(Float, nullable=False)
    title = Column(Text, nullable=False)
    owner = Column(ShortCls, nullable=False, index=True)
    exclusion = Column(Geometry)

    __mapper_args__ = {
        'polymorphic_identity': SectorType.SECTOR,
        'polymorphic_on': 'type'
    }

    @classmethod
    def provides(cls, s, pipeline):
        pipeline._provides(s, T.SECTOR_TIME, StatisticJournalType.FLOAT, U.S, S.join(S.MIN, S.CNT, S.MSR),
                           'The time to complete the sector.')
        pipeline._provides(s, T.SECTOR_DISTANCE, StatisticJournalType.FLOAT, U.KM, None,
                           'The sector distance.')

    def add_statistics(self, s, sjournal, loader):
        loader.add_data(N.SECTOR_TIME, sjournal, (sjournal.finish - sjournal.start).total_seconds(), sjournal.start)
        loader.add_data(N.SECTOR_DISTANCE, sjournal, sjournal.distance, sjournal.start)


@add_child_ddl(Sector)
class SectorClimb(Sector):

    __tablename__ = 'sector_climb'

    id = Column(Integer, ForeignKey('sector.id', ondelete='cascade'), primary_key=True)
    category = Column(Text)
    elevation = Column(Float, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': SectorType.CLIMB
    }

    # these don't delegate to parent because we want to use different names for basically the same thing

    @classmethod
    def provides(cls, s, pipeline):
        pipeline._provides(s, T.CLIMB_ELEVATION, StatisticJournalType.FLOAT, U.M, S.join(S.MAX, S.SUM, S.MSR),
                           'The difference in elevation between start and end of the climb.')
        pipeline._provides(s, T.CLIMB_DISTANCE, StatisticJournalType.FLOAT, U.KM, S.join(S.MAX, S.SUM, S.MSR),
                           'The distance travelled during the climb.')
        pipeline._provides(s, T.CLIMB_TIME, StatisticJournalType.FLOAT, U.S, S.join(S.MAX, S.SUM, S.MSR),
                           'The time spent on the climb.')
        pipeline._provides(s, T.CLIMB_GRADIENT, StatisticJournalType.FLOAT, U.PC,  S.join(S.MAX, S.MSR),
                           'The average inclination of the climb (elevation / distance).')
        # pipeline._provides(s, T.CLIMB_POWER, StatisticJournalType.FLOAT, U.W,  S.join(S.MAX, S.MSR),
        #                    'The average estimated power during the climb.')
        pipeline._provides(s, T.CLIMB_CATEGORY, StatisticJournalType.TEXT, None, None,
                           'The climb category (text, "4" to "1" and "HC").')

    def add_statistics(self, s, sjournal, loader):
        loader.add_data(N.CLIMB_ELEVATION, sjournal, self.elevation, sjournal.start)
        loader.add_data(N.CLIMB_DISTANCE, sjournal, self.distance, sjournal.start)
        loader.add_data(N.CLIMB_TIME, sjournal, (sjournal.finish - sjournal.start).total_seconds(), sjournal.start)
        loader.add_data(N.CLIMB_GRADIENT, sjournal, self.elevation / (10 * self.distance), sjournal.start)
        if self.category:
            loader.add_data(N.CLIMB_CATEGORY, sjournal, self.category, sjournal.start)
