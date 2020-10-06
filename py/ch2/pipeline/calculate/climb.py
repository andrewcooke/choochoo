from logging import getLogger

from sqlalchemy import text

from .utils import ActivityJournalCalculatorMixin
from ..pipeline import OwnerInMixin
from ...common.date import local_time_to_time
from ...sql import Timestamp

log = getLogger(__name__)


class ClimbCalculator(OwnerInMixin, ActivityJournalCalculatorMixin):

    def _run_one(self, missed):
        start = local_time_to_time(missed)
        with self._config.db.session_context() as s:
            ajournal = self._get_source(s, start)
            with Timestamp(owner=self.owner_out, source=ajournal).on_success(s):
                pass

    def __non_climb_lines(self, s, sector_group_id, activity_journal_id, radius=20):
        sql = text('''
  with climbs as (select st_collect(st_buffer(route, :width, 'endcap=flat')) as climb
                    from sector
                   where sector_group_id = :sector_group_id
                     and owner = 'foo'),
       lines as (select st_dump(st_difference(st_transform(aj.route::geometry, sg.srid), c.climb)) as gap
                   from activity_journal as aj,
                        climbs as c,
                        sector_group as sg
                  where aj.id = :activity_journal_id
                    and sg.id = :sector_group_id
                    and st_distance(sg.centre, aj.centre) < sg.radius),
       points as (select st_dump((line).geom) as point,
                         (line).path[1]
                    from lines) 
select st_x((point).geom) as x, st_y((point).geom) as y, st_m((point).geom) as t, path
  from points;
        ''')
        log.debug(sql)
