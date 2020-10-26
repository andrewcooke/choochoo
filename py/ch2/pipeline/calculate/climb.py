import datetime as dt
from json import loads
from logging import getLogger

import pandas as pd
from sqlalchemy import text, func
from sqlalchemy.exc import IntegrityError

from .elevation import expand_distance_time, elapsed_time_to_time
from .utils import ActivityJournalProcessCalculator
from ...common.date import local_time_to_time
from ...common.log import log_current_exception
from ...data.sector import add_start_finish
from ...names import N
from ...sql import Timestamp, Constant
from ...sql.tables.sector import SectorGroup, Sector, SectorClimb
from ...sql.types import Point
from ...sql.utils import add

log = getLogger(__name__)


class FindClimbCalculator(ActivityJournalProcessCalculator):

    def __init__(self, *args, climb=None, **kargs):
        super().__init__(*args, **kargs)
        self.__climb_ref = climb

    def _startup(self, s):
        from ...data.climb import Climb
        super()._startup(s)
        self.__climb = Climb(**loads(Constant.from_name(s, self.__climb_ref).at(s).value))

    def _run_one(self, missed):
        start = local_time_to_time(missed)
        with self._config.db.session_context() as s:
            ajournal = self._get_source(s, start)
            with Timestamp(owner=self.owner_out, source=ajournal).on_success(s):
                if ajournal.route_edt:
                    for sector_group in s.query(SectorGroup). \
                            filter(func.st_distance(SectorGroup.centre, Point.fmt(ajournal.centre))
                                   < SectorGroup.radius). \
                            all():
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
        log.info('Finding climbs from the entire route')
        df = self.__complete_route(s, sector_group.id, ajournal.id)
        df = expand_distance_time(df)
        df = elapsed_time_to_time(df, ajournal.start)
        df = df.set_index(df[N.TIME]).drop(columns=[N.TIME])
        for climb in find_climbs(df, params=self.__climb):
            log.info(f'Have a climb (elevation {climb[N.CLIMB_ELEVATION]})')
            self.__register_climb(s, df, climb, sector_group, ajournal.id)

    def __register_climb(self, s, df, climb, sector_group, activity_journal_id):
        df = df.loc[climb[N.TIME] - dt.timedelta(seconds=climb[N.CLIMB_TIME]) : climb[N.TIME]]
        points = [f'ST_MakePoint({row.x}, {row.y})' for row in df.itertuples()]
        route = f'ST_MakeLine(ARRAY[{", ".join(points)}])'
        box = f'Box2D({route})'
        while True:
            try:
                climb = self.__add_climb(s, sector_group, climb, route, box, activity_journal_id)
                s.commit()
                add_start_finish(s, climb.id)
                s.commit()
                log.info('Added climb')
                return
            except IntegrityError:
                s.rollback()
                # we want to remove the previous climb if:
                # 1 - the existing climb is 'the same' but larger (we want to match with the smallest so
                #     we catch all)
                # 2 - the existing climb is much smaller (we want to match larger climbs in general)
                removed = self.__remove_slightly_bigger(s, sector_group, box, climb[N.CLIMB_ELEVATION])
                s.commit()
                removed = self.__remove_much_smaller(s, sector_group, box, climb[N.CLIMB_ELEVATION]) or removed
                s.commit()
                if not removed:
                    log.info('Climb was blocked by existing climb')
                    return

    def __remove_slightly_bigger(self, s, sector_group, box, elevation):
        query = s.query(Sector.id). \
            join(SectorClimb). \
            filter(Sector.sector_group == sector_group,
                   Sector.owner == self,
                   SectorClimb.elevation.between(elevation, 1.1 * elevation),
                   Sector.exclusion.intersects(text(box)))
        n = query.count()
        if n:
            log.info(f'Deleting {n} slightly bigger climbs')
            s.query(Sector).filter(Sector.id.in_(query)).delete(synchronize_session=False)
        return n

    def __remove_much_smaller(self, s, sector_group, box, elevation):
        query = s.query(Sector.id). \
            join(SectorClimb). \
            filter(Sector.sector_group == sector_group,
                   Sector.owner == self,
                   SectorClimb.elevation < 0.9 * elevation,
                   Sector.exclusion.intersects(text(box)))
        n = query.count()
        if n:
            log.info(f'Deleting {n} much smaller climbs')
            s.query(Sector).filter(Sector.id.in_(query)).delete(synchronize_session=False)
        return n

    def __add_climb(self, s, sector_group, climb, route, box, activity_journal_id):
        if N.CLIMB_CATEGORY in climb:
            title = f'Climb (cat {climb[N.CLIMB_CATEGORY]})'
        else:
            title = f'Climb (uncat)'
        category = climb.get(N.CLIMB_CATEGORY, None)
        # text because we're passing in direct SQL functions, not EWKT
        climb = add(s, SectorClimb(sector_group=sector_group, activity_journal_id=activity_journal_id,
                                   route=text(route), title=title, owner=self, exclusion=text(box),
                                   distance=climb[N.CLIMB_DISTANCE], category=category,
                                   elevation=climb[N.CLIMB_ELEVATION]))
        s.flush()
        return climb

    def __complete_route(self, s, sector_group_id, activity_journal_id):
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
