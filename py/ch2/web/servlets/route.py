from logging import getLogger

from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape
from sqlalchemy import text
import pandas as pd

from .sector import ActivityBase
from ...names import N
from ...pipeline.calculate.elevation import expand_distance_time
from ...sql.tables.sector import SectorJournal
from ...sql.utils import WGS84_SRID

log = getLogger(__name__)


class Route(ActivityBase):

    def read_activity_latlon(self, request, s, activity):
        return {'latlon': self._read_activity_route(s, activity),
                'sectors': list(self._read_sectors(s, activity))}

    def _wkb_to_latlon(self, wkb):
        return [(lat, lon) for (lon, lat) in to_shape(wkb).coords]

    def _read_activity_route(self, s, activity_journal_id):
        return self._wkb_to_latlon(self._read_activity_route_wkb(s, activity_journal_id))

    def _read_activity_route_wkb(self, s, activity_journal_id):
        q = text(f'''
select st_force2d(aj.route_et::geometry)
  from activity_journal as aj
 where aj.id = :activity_journal_id''')
        return WKBElement(s.connection().execute(q, activity_journal_id=activity_journal_id).fetchone()[0])

    def _read_sectors(self, s, activity):
        for sjournal in s.query(SectorJournal).filter(SectorJournal.activity_journal_id == activity).all():
            yield {'latlon': self._read_sector_route(s, sjournal.sector.id),
                   'type': sjournal.sector.type,
                   'db': sjournal.sector.id}  # todo - probably want tuple w 'climb' etc here

    def _read_sector_route(self, s, sector_id):
        q = text(f'''
select st_transform(st_setsrid(s.route, sg.srid), {WGS84_SRID})
  from sector as s,
       sector_group as sg
 where s.id = :sector_id''')
        return self._wkb_to_latlon(WKBElement(s.connection().execute(q, sector_id=sector_id).fetchone()[0]))

    def read_sector_latlon(self, request, s, sector):
        return {'latlon': self._read_sector_route(s, sector)}

    def read_sector_edt(self, request, s, sector):
        # this is actually sector_journal
        df = self._read_clipped_d_et(s, sector)
        return {
            # 'elevation': (df[N.ELEVATION] - df[N.ELEVATION].min()).tolist(),
            'elevation': df[N.ELEVATION].tolist(),
            'distance': (df[N.DISTANCE] - df[N.DISTANCE].iloc[0]).tolist(),
            'time': (df[N.ELAPSED_TIME] - df[N.ELAPSED_TIME].iloc[0]).tolist()}

    def _read_clipped_d_et(self, s, sector_journal_id):
        # cannot use route_edt because we need to substring / interpolate
        sql = text(f'''
  with points as (select st_dumppoints(
                            st_linesubstring(
                              aj.route_d::geometry, sj.start_fraction, sj.finish_fraction)) as point
                    from activity_journal as aj,
                         sector_journal as sj
                   where sj.id = :sector_journal_id
                     and aj.id = sj.activity_journal_id)
select st_x((point).geom) as x, st_y((point).geom) as y, st_m((point).geom) as {N.DISTANCE}
  from points;
''')
        log.debug(sql)
        df_d = pd.read_sql(sql, s.connection(),
                           params={'sector_journal_id': sector_journal_id})
        sql = text(f'''
  with points as (select st_dumppoints(
                            st_linesubstring(
                              aj.route_et::geometry, sj.start_fraction, sj.finish_fraction)) as point
                    from activity_journal as aj,
                         sector_journal as sj
                   where sj.id = :sector_journal_id
                     and aj.id = sj.activity_journal_id)
select st_x((point).geom) as x, st_y((point).geom) as y, st_z((point).geom) as {N.ELEVATION},
       st_m((point).geom) as "{N.ELAPSED_TIME}"
  from points;
''')
        log.debug(sql)
        df_et = pd.read_sql(sql, s.connection(),
                            params={'sector_journal_id': sector_journal_id})
        df = pd.merge(df_et, df_d, how='left', left_on=['x', 'y'], right_on=['x', 'y']).dropna()
        return df
