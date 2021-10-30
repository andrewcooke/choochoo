from logging import getLogger

import pandas as pd
from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape
from sqlalchemy import text

from . import ContentType
from ...names import N
from ...pipeline.calculate.elevation import expand_distance_time
from ...sql.tables.sector import SectorJournal
from ...sql.utils import WGS84_SRID

log = getLogger(__name__)


class Route(ContentType):

    def read_activity_latlon(self, request, s, activity):
        df = expand_distance_time(self._read_activity_route(s, activity))
        latlon = list(df[[N.LATITUDE, N.LONGITUDE]].itertuples(index=None, name=None))
        elevation = list(df[[N.DISTANCE, N.ELEVATION]].itertuples(index=None, name=None))
        return {'latlon': latlon,
                'elevation': elevation,
                'sectors': list(self._read_sectors(s, activity))}

    def _read_activity_route(self, s, activity_journal_id):
        return read_activity_route(s, activity_journal_id)

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

    def _wkb_to_latlon(self, wkb):
        return [(lat, lon) for (lon, lat) in to_shape(wkb).coords]

    def read_sector_latlon(self, request, s, sector):
        return {'latlon': self._read_sector_route(s, sector)}


def read_activity_route(s, activity_journal_id):
    """
    Reads in the coord system of the activity, so WGS84 lat lon.
    """
    sql = text(f'''
  with points as (select st_dumppoints(aj.route_edt::geometry) as point
                    from activity_journal as aj
                   where aj.id = :activity_journal_id)
select st_x((point).geom) as {N.LONGITUDE}, st_y((point).geom) as {N.LATITUDE}, 
       st_z((point).geom) as {N.ELEVATION}, st_m((point).geom) as "{N.DISTANCE_TIME}"
  from points;
        ''')
    log.debug(sql)
    return pd.read_sql(sql, s.connection(),
                       params={'activity_journal_id': activity_journal_id})
