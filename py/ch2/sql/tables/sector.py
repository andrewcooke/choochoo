from enum import IntEnum
from logging import getLogger

from geoalchemy2 import Geometry, WKTElement, Geography
from geoalchemy2.shape import to_shape
from sqlalchemy import Column, Integer, Text, ForeignKey, Float, UniqueConstraint, or_, func, text
from sqlalchemy.orm import relationship

from .source import GroupedSource, Source, SourceType
from .statistic import StatisticJournalType
from ..support import Base
from ..triggers import add_child_ddl, add_text
from ..types import ShortCls, UTC, point
from ..utils import add, SPHM_SRID, WGS84_SRID
from ...common.geo import utm_srid
from ...common.plot import CYAN
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
    start_elevation = Column(Float, nullable=False)
    finish_elevation = Column(Float, nullable=False)
    UniqueConstraint(sector_id, activity_journal_id, start_fraction, finish_fraction)

    __mapper_args__ = {
        'polymorphic_identity': SourceType.SECTOR
    }

    def time_range(self, s):
        return self.start_time, self.finish_time

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
    centre = Column(Geography('Point', srid=WGS84_SRID), nullable=False)
    radius = Column(Float, nullable=False)  # metres
    title = Column(Text, nullable=False)
    UniqueConstraint(centre, radius, title)

    @classmethod
    def add(cls, s, centre, radius_km, title, delete=False):
        '''
        if delete is True, nearby similar entries are deleted before insertion.
        if delete is False, and there is already a nearby similar entry, it is returned.
        otherwise, insertion is attempted without deletion.
        centre is (lon, lat)
        '''
        lon, lat = centre
        srid = utm_srid(lat, lon)
        centre = text(point(lon, lat))
        radius = radius_km * 1000
        if delete is not None:
            query = s.query(SectorGroup). \
                filter(func.ST_Distance(SectorGroup.centre, centre) < radius,
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


class Sector(Base):

    __tablename__ = 'sector'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, nullable=False, index=True)  # index needed for fast delete of subtypes
    sector_group_id = Column(Integer, ForeignKey('sector_group.id', ondelete='cascade'), nullable=False)
    sector_group = relationship('SectorGroup')
    # this used only for debugging (sectors should be independent of original activity)
    activity_journal_id = Column(Integer, ForeignKey('activity_journal.id'), index=True)
    route = Column(Geometry('LineString'), nullable=False)
    distance = Column(Float, nullable=False)
    title = Column(Text, nullable=False)
    owner = Column(ShortCls, nullable=False, index=True)
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

    def add_statistics(self, s, sjournal, loader, **kargs):
        loader.add_data(N.SECTOR_TIME, sjournal, (sjournal.finish_time - sjournal.start_time).total_seconds(),
                        sjournal.start_time)
        loader.add_data(N.SECTOR_DISTANCE, sjournal, sjournal.finish_distance - sjournal.start_distance,
                        sjournal.start_time)

    def read_path(self, s):
        sql = text(f'''
select st_astext(st_transform(st_setsrid(s.route, sg.srid), {SPHM_SRID}))
  from sector as s,
       sector_group as sg
 where s.id = :sector_id
   and sg.id = s.sector_group_id
    ''')
        row = s.connection().execute(sql, sector_id=self.id).fetchone()
        return to_shape(WKTElement(row[0])).xy

    def display(self, s, fx, fy, ax, cm=1.5):
        xs, ys = self.read_path(s)
        ax.plot([fx(x) for x in xs], [fy(y) for y in ys], color=CYAN)


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
        pipeline._provides(s, T.VERTICAL_POWER, StatisticJournalType.FLOAT, U.W,  S.join(S.MAX, S.MSR),
                           'The estimated power for the climb considering only weight / height.')
        pipeline._provides(s, T.CLIMB_CATEGORY, StatisticJournalType.TEXT, None, None,
                           'The climb category (text, "4" to "1" and "HC").')

    def add_statistics(self, s, sjournal, loader, power_model=None, **kargs):
        # these are taken from the actial activity, not the sector, so will vary from match to match
        elevation = sjournal.finish_elevation - sjournal.start_elevation
        distance = sjournal.finish_distance - sjournal.start_distance
        loader.add_data(N.CLIMB_ELEVATION, sjournal, elevation, sjournal.start_time)
        loader.add_data(N.CLIMB_DISTANCE, sjournal, distance, sjournal.start_time)
        loader.add_data(N.CLIMB_TIME, sjournal, (sjournal.finish_time - sjournal.start_time).total_seconds(),
                        sjournal.start_time)
        loader.add_data(N.CLIMB_GRADIENT, sjournal, elevation / (10 * distance), sjournal.start_time)
        if self.category:
            loader.add_data(N.CLIMB_CATEGORY, sjournal, self.category, sjournal.start_time)
        if power_model:
            power = self._estimate_power(s, sjournal, power_model)
            loader.add_data(N.VERTICAL_POWER, sjournal, power, sjournal.start_time)

    def _estimate_power(self, s, sjournal, power_model, g=9.8):
        from ...data.query import interpolate
        from ...pipeline.read.activity import ActivityReader
        speed_start = interpolate(s, sjournal.activity_journal, N.SPEED, ActivityReader, sjournal.start_time)
        speed_finish = interpolate(s, sjournal.activity_journal, N.SPEED, ActivityReader, sjournal.finish_time)
        total_weight = power_model.bike_model.bike_weight + power_model.rider_weight
        energy_after = 0.5 * total_weight * speed_finish ** 2 + total_weight * g * self.elevation
        energy_before = 0.5 * total_weight * speed_start ** 2
        return (energy_after - energy_before) / (sjournal.finish_time - sjournal.start_time).total_seconds()

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
