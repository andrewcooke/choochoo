from logging import getLogger

from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape
from sqlalchemy import text

from . import ContentType
from ..json import JsonResponse
from ...sql.tables.sector import SectorJournal
from ...sql.utils import WGS84_SRID

log = getLogger(__name__)


class Route(ContentType):

    def __call__(self, request, s, activity):
        return JsonResponse({'latlon': self._read_activity_route(s, activity),
                             'sectors': list(self._read_sectors(s, activity))})

    def _wkb_to_latlon(self, wkb):
        return [(lat, lon) for (lon, lat) in to_shape(wkb).coords]

    def _read_activity_route(self, s, activity_journal_id):
        q = text(f'''
select st_force2d(aj.route_t::geometry)
  from activity_journal as aj
 where aj.id = :activity_journal_id''')
        return self._wkb_to_latlon(WKBElement(s.connection().execute(q, activity_journal_id=activity_journal_id).fetchone()[0]))

    def _read_sectors(self, s, activity):
        for sjournal in s.query(SectorJournal).filter(SectorJournal.activity_journal_id == activity).all():
            yield {'latlon': self._read_sector_route(s, sjournal.sector.id),
                   'db': sjournal.sector.id}  # todo - probably want tuple w 'climb' etc here

    def _read_sector_route(self, s, sector_id):
        q = text(f'''
select st_transform(st_setsrid(s.route, sg.srid), {WGS84_SRID})
  from sector as s,
       sector_group as sg
 where s.id = :sector_id''')
        return self._wkb_to_latlon(WKBElement(s.connection().execute(q, sector_id=sector_id).fetchone()[0]))
