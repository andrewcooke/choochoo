from enum import IntEnum
from logging import getLogger

from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, Text, ForeignKey, Float, UniqueConstraint, or_, func, and_, select, text
from sqlalchemy.orm import relationship

from .source import GroupedSource, Source, SourceType
from .statistic import StatisticJournalType
from ..support import Base
from ..triggers import add_child_ddl, add_text
from ..types import ShortCls, Point, UTC
from ..utils import add
from ...common.geo import utm_srid
from ...common.plot import ORANGE, LIME, CYAN
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
    start_fraction = Column(Float, nullable=False)
    finish_fraction = Column(Float, nullable=False)
    # these duplicate data (can be extracted from st_linesubstring and the activity route)
    # but simplify time_range below.
    start_time = Column(UTC, nullable=False)
    finish_time = Column(UTC, nullable=False)
    # this duplicates data because it's useful and a pain to calculate separately
    start_distance = Column(Float, nullable=False)
    finish_distance = Column(Float, nullable=False)
    UniqueConstraint(sector_id, activity_journal_id, start_fraction, finish_fraction)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.SECTOR
    }

    def time_range(self, s):
        return self.start, self.finish

    @classmethod
    def clean(cls, s):
        q1 = s.query(SectorJournal.id). \
            filter(or_(SectorJournal.sector_id == None,
                       SectorJournal.activity_journal_id == None)).cte()
        s.query(Source).filter(Source.id.in_(q1)).delete(synchronize_session=False)


class SectorGroup(Base):
    '''
    this is not owned by anything (sectors are owned individually).
    rather, it defines a place where we are interested in all kinds of sectors -
    typically, the geographical region where the user lives.
    we could even try setting it algorithmically from a few activities.
    '''

    __tablename__ = 'sector_group'

    id = Column(Integer, primary_key=True)
    srid = Column(Integer, nullable=False)
    centre = Column(Point, nullable=False)
    radius = Column(Float, nullable=False)  # metres
    title = Column(Text, nullable=False)
    UniqueConstraint(centre, radius, title)

    @classmethod
    def add(cls, s, centre, radius_km, title, delete=False):
        '''
        if delete is True, nearby similar entries are deleted before insertion.
        if delete is False, and there is already a nearby similar entry, it is returned.
        otherwise, insertion is attempted without deletion.
        '''
        lon, lat = centre
        srid = utm_srid(lat, lon)
        radius = radius_km * 1000
        if delete is not None:
            query = s.query(SectorGroup). \
                filter(func.ST_Distance(SectorGroup.centre, Point.fmt(centre)) < radius,
                       SectorGroup.srid == srid)
            n = query.count()
            if delete:
                if n:
                    log.warning(f'Deleting {n} previous sector groups')
                    query.delete(synchronize_session=False)
            else:
                if n:
                    sector_group = query.first()
                    log.info(f'Using previously defined sector group "{sector_group.title}"')
                    return sector_group
        return add(s, SectorGroup(srid=srid, centre=centre, radius=radius, title=title))


class SectorType(IntEnum):
    '''
    different owners don't need to defin their own types.
    the subclasses are mainly for display (climb has elevation and category and is displayed differently)
    '''

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
    # this used only for debugging (it should not matter)
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id'), index=True)
    route = Column(Geometry('LineString'), nullable=False)
    distance = Column(Float, nullable=False)
    title = Column(Text, nullable=False)
    owner = Column(ShortCls, nullable=False, index=True)
    exclusion = Column(Geometry)
    # null because set later (calculated from route but stored for efficiency)
    start = Column(Geometry('LineString'))
    finish = Column(Geometry('LineString'))
    hull = Column(Geometry('Polygon'))

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
        loader.add_data(N.SECTOR_TIME, sjournal, (sjournal.finish_time - sjournal.start_time).total_seconds(),
                        sjournal.start_time)
        loader.add_data(N.SECTOR_DISTANCE, sjournal, sjournal.finish_distance - sjournal.start_distance,
                        sjournal.start_time)

    def read_centroid(self, s):
        sql = text('''
      with point as (select st_centroid(st_transform(st_setsrid(s.route, sg.srid), 3785)) as point
                       from sector as s,
                            sector_group as sg
                      where s.sector_group_id = sg.id
                        and s.id = :sector_id)
    select st_x(point), st_y(point)
      from point; 
    ''')
        row = s.connection().execute(sql, sector_id=self.id).fetchone()
        return row[0], row[1]

    def display(self, s, fx, fy, ax, cm=1.5):
        x, y = self.read_centroid(s)
        ax.plot(fx(x), fy(y), marker='^', color=CYAN, markersize=cm*3)



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
        # note that apart from time these are taken from the sector rather than the journal
        # this is deliberate - seems like we want these climbs to be consistent.
        loader.add_data(N.CLIMB_ELEVATION, sjournal, self.elevation, sjournal.start_time)
        loader.add_data(N.CLIMB_DISTANCE, sjournal, self.distance, sjournal.start_time)
        loader.add_data(N.CLIMB_TIME, sjournal, (sjournal.finish_time - sjournal.start_time).total_seconds(),
                        sjournal.start_time)
        loader.add_data(N.CLIMB_GRADIENT, sjournal, self.elevation / (10 * self.distance), sjournal.start_time)
        if self.category:
            loader.add_data(N.CLIMB_CATEGORY, sjournal, self.category, sjournal.start_time)
