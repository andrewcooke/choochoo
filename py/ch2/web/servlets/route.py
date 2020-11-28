from logging import getLogger

from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape
from sqlalchemy import text

from . import ContentType
from ...data.sector import add_start_finish
from ...sql import ActivityJournal, Sector
from ...sql.tables.sector import SectorJournal, SectorGroup, DEFAULT_GROUP_RADIUS_KM, SectorType
from ...sql.types import short_cls, linestringxy
from ...sql.utils import WGS84_SRID, add

log = getLogger(__name__)


class Route(ContentType):

    def read_activity(self, request, s, activity):
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

    def create_sector(self, request, s, activity):
        data = request.json
        activity_journal = s.query(ActivityJournal).filter(ActivityJournal.id == activity).one()
        sector_group = SectorGroup.add(s, to_shape(activity_journal.centre).coords[0],
                                       DEFAULT_GROUP_RADIUS_KM,
                                       f'From activity on {activity_journal.start}')
        full_route = to_shape(self._read_activity_route_wkb(s, activity))
        new_route = full_route.coords[data['start']:data['finish']]
        ls_route = linestringxy(new_route)
        srid_route = f'st_transform(st_setsrid({ls_route}, {WGS84_SRID}), {sector_group.srid})'
        sector = add(s, Sector(type=SectorType.SECTOR, sector_group=sector_group,
                               activity_journal_id=activity, route=text(srid_route),
                               title=data['name'], owner=self))
        s.flush()
        add_start_finish(s, sector.id)
        s.commit()
        return {'sector': sector.id}
