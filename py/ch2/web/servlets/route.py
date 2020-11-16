from logging import getLogger

from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape
from sqlalchemy import text

from . import ContentType
from ..json import JsonResponse
from ...sql.tables.sector import SectorJournal
from ...sql.utils import SPHM_SRID

log = getLogger(__name__)


class Route(ContentType):

    def __call__(self, request, s, activity):
        return JsonResponse({'latlon': self._read_route(s, activity),
                             'sectors': list(self._read_sectors(s, activity))})

    def _wkb_to_latlon(self, wkb):
        return [(int(lat), int(lon)) for (lon, lat) in to_shape(wkb).coords]

    def _read_route(self, s, activity):
        q = text(f'''
select st_force2d(st_transform(aj.route_t::geometry, {SPHM_SRID}))
  from activity_journal as aj
 where aj.id = :activity_journal_id''')
        return self._wkb_to_latlon(WKBElement(s.connection().execute(q, activity_journal_id=activity).fetchone()[0]))

    def _read_sectors(self, s, activity):
        for sjournal in s.query(SectorJournal).filter(SectorJournal.activity_journal_id == activity).all():
            yield {'latlon': self._wkb_to_latlon(sjournal.sector.route),
                   'db': sjournal.sector.id}  # todo - probably want tuple w 'climb' etc here
