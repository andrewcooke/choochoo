import datetime as dt
from json import loads
from logging import getLogger

import pandas as pd
from sqlalchemy import text, func

from ch2.commands.args import DARK
from ch2.data.climb import find_climbs, MIN_CLIMB_GRADIENT, MAX_CLIMB_GRADIENT, MIN_CLIMB_ELEVATION, MAX_CLIMB_REVERSAL, \
    CLIMB_PHI, Climb
from ch2.lib.log import make_log
from ch2.sql.database import Database
from .elevation import expand_distance_time, elapsed_time_to_time
from .utils import ActivityGroupProcessCalculator
from ...common.date import local_time_to_time
from ...common.log import log_current_exception
from ...data.sector import add_start_finish
from ...names import N
from ...sql import Timestamp, Constant, Sector, SectorGroup, SectorClimb, ActivityJournal
from ...sql.types import linestringxy
from ...sql.utils import add

log = getLogger(__name__)

DISTINCT_CLIMB = 0.5


class FindClimbCalculator(ActivityGroupProcessCalculator):

    def __init__(self, *args, climbs=None, **kargs):
        super().__init__(*args, **kargs)
        self.__climbs_ref = climbs

    def _startup(self, s):
        from ...data.climb import Climb
        super()._startup(s)
        self.__climbs = [Climb(**loads(Constant.from_name(s, climb).at(s).value))
                         for climb in self.__climbs_ref.split(',')]

    def _shutdown(self, s):
        super()._shutdown(s)
        if not self.worker:
            log.info('Checking for extra prunes')
            n_climbs, n_prunes = 0, 0
            for row in s.query(SectorClimb.id).all():
                if self.__prune_climb(s, row.id):
                    n_prunes += 1
                else:
                    n_climbs += 1
            log.info(f'Total {n_climbs} climbs ({n_prunes} pruned)')

    def _run_one(self, missed):
        start = local_time_to_time(missed)
        with self._config.db.session_context() as s:
            ajournal = self._get_source(s, start)
            with Timestamp(owner=self.owner_out, source=ajournal).on_success(s):
                if ajournal.route_edt:
                    for sector_group in SectorGroup.near(s, ajournal.centre):
                        log.info(f'Finding climbs for activity journal {ajournal.id} / sector group {sector_group.id}')
                        try:
                            self.__find_big_climbs(s, sector_group, ajournal)
                        except Exception as e:
                            log.warning(f'Climb detection failed with {e} for activity journal {ajournal.id} '
                                        f'and sector group {sector_group.id}')
                            log_current_exception(True)
                            s.rollback()

    def __find_big_climbs(self, s, sector_group, ajournal):
        from ...data.climb import find_climbs
        df = self.__read_complete_route(s, sector_group.id, ajournal.id)
        df = expand_distance_time(df)
        df = elapsed_time_to_time(df, ajournal.start)
        df = df.set_index(df[N.TIME]).drop(columns=[N.TIME])
        for params in self.__climbs:
            for climb in find_climbs(df, params=params):
                log.info(f'Have a climb (elevation {climb[N.CLIMB_ELEVATION]})')
                self.__register_climb(s, df, climb, sector_group, ajournal.id)

    def __read_complete_route(self, s, sector_group_id, activity_journal_id):
        return read_activity_route_for_sector_group(s, activity_journal_id, sector_group_id)

    def __register_climb(self, s, df, climb_id, sector_group, activity_journal_id):
        # this is not easy
        # we cannot exclude climbs based on a constraint (it's too complex)
        # we are loading in parallel, so don't have a clear idea of what other climbs exist at any one point in time
        # so what we do is load all climbs and then delete conflicts
        # deletion always respects earlier (smaller ID) climbs, so we get something similar(?) to what we
        # would get if all loaded in order
        df = df.loc[climb_id[N.TIME] - dt.timedelta(seconds=climb_id[N.CLIMB_TIME]): climb_id[N.TIME]]
        route = linestringxy([(row.x, row.y) for row in df.itertuples()], type='geometry')
        climb_id = self.__add_climb(s, sector_group, climb_id, route, activity_journal_id)
        add_start_finish(s, climb_id)
        log.debug(f'Added climb {climb_id}')
        self.__prune_climb(s, climb_id)
        s.commit()

    def __add_climb(self, s, sector_group, climb, route, activity_journal_id):
        if N.CLIMB_CATEGORY in climb:
            title = f'Climb (cat {climb[N.CLIMB_CATEGORY]})'
        else:
            title = f'Climb (uncat)'
        category = climb.get(N.CLIMB_CATEGORY, None)
        # text because we're passing in direct SQL functions, not EWKT
        climb = add(s, SectorClimb(sector_group=sector_group, route=text(route), title=title, owner=self,
                                   distance=climb[N.CLIMB_DISTANCE], category=category,
                                   elevation=climb[N.CLIMB_ELEVATION]))
        s.flush()
        return climb.id

    def __prune_climb(self, s, climb_id):
        sql = text(f'''
  with candidates as (select st_length(st_setsrid(b.route, sg.srid)) as l1,
                             st_length(st_difference(st_setsrid(b.route, sg.srid), st_setsrid(s.hull, sg.srid))) as l2,
                             st_length(st_setsrid(s.route, sg.srid)) as l3,
                             st_length(st_difference(st_setsrid(s.route, sg.srid), st_setsrid(b.hull, sg.srid))) as l4
                        from sector as b,
                             sector as s,
                             sector_group as sg
                       where s.id = :climb_id
                         and b.id < s.id
                         and sg.id = s.sector_group_id
                         and sg.id = b.sector_group_id
                         and st_intersects(st_setsrid(b.route, sg.srid), st_setsrid(s.hull, sg.srid)))
select count(1)
  from candidates as c
 where l2 / l1 < {DISTINCT_CLIMB}
   and l4 / l3 < {DISTINCT_CLIMB}
''')
        if s.connection().execute(sql, climb_id=climb_id).scalar():
            log.debug(f'Deleting climb {climb_id}')
            s.query(Sector).filter(Sector.id == climb_id).delete(synchronize_session=False)
            return True
        else:
            return False


def read_activity_route_for_sector_group(s, activity_journal_id, sector_group_id):
    """
    Reads in the coord system of the sector group (so typically m in some local mercator projection).
    """
    sql = text(f'''
with points as (select st_dumppoints(st_transform(aj.route_edt::geometry, sg.srid)) as point
                from activity_journal as aj,
                     sector_group as sg
               where aj.id = :activity_journal_id
                 and sg.id = :sector_group_id
                 and st_distance(sg.centre, aj.centre) < sg.radius)
select st_x((point).geom) as x, st_y((point).geom) as y, 
   st_z((point).geom) as {N.ELEVATION}, st_m((point).geom) as "{N.DISTANCE_TIME}"
from points;
    ''')
    log.debug(sql)
    df = pd.read_sql(sql, s.connection(),
                     params={'sector_group_id': sector_group_id,
                             'activity_journal_id': activity_journal_id})
    return df


# allow manual run with data to corral quemado

if __name__ == '__main__':
    make_log('/tmp/test.log', 5, DARK)
    db = Database('postgresql://default:@localhost:5432/activity-0-41')
    with db.session_context() as s:
        activity_journal = ActivityJournal.at(s, '2021-10-19')
        sector_group = list(SectorGroup.near(s, activity_journal.centre))[0]
        df = read_activity_route_for_sector_group(s, activity_journal.id, sector_group.id)
        df = expand_distance_time(df)
        df = elapsed_time_to_time(df, activity_journal.start)
        df = df.set_index(df[N.TIME]).drop(columns=[N.TIME])
        params = Climb(phi=CLIMB_PHI,
                       min_gradient=MIN_CLIMB_GRADIENT,
                       max_gradient=MAX_CLIMB_GRADIENT,
                       min_elevation=MIN_CLIMB_ELEVATION,
                       max_reversal=MAX_CLIMB_REVERSAL)
        for climb in find_climbs(df, params=params):
            print(f'Have a climb (elevation {climb[N.CLIMB_ELEVATION]})')
            print(climb)
