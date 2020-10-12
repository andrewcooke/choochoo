import datetime as dt
from json import loads
from logging import getLogger

import pandas as pd
from sqlalchemy import text, func
from sqlalchemy.exc import IntegrityError

from .elevation import expand_distance_time, ElevationCalculator, elapsed_time_to_time
from .utils import ActivityJournalCalculatorMixin, ProcessCalculator
from ..read.segment import SegmentReader
from ...common.date import local_time_to_time
from ...common.log import log_current_exception
from ...data import Statistics
from ...data.climb import find_climbs
from ...names import N
from ...sql import Timestamp, Constant
from ...sql.tables.sector import SectorGroup, Sector, Climb
from ...sql.types import short_cls
from ...sql.utils import add

log = getLogger(__name__)


class FindClimbCalculator(ActivityJournalCalculatorMixin, ProcessCalculator):

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
                            filter(func.st_distance(SectorGroup.centre, ajournal.centre) < SectorGroup.radius). \
                            all():
                        try:
                            self.__find_big_climbs(s, sector_group, ajournal)
                            # doesn't add anything new
                            # self.__find_small_climbs(s, sector_group, ajournal)
                        except Exception as e:
                            log.warning(f'Climb detection failed with {e} for activity journal {ajournal.id} '
                                        f'and sector group {sector_group.id}')
                            log_current_exception(True)
                            s.rollback()

    def __find_big_climbs(self, s, sector_group, ajournal):
        log.info('Finding climbs from the entire route')
        df = self.__complete_route(s, sector_group.id, ajournal.id)
        df = expand_distance_time(df)
        df = df.set_index(df[N.TIME]).drop(columns=[N.TIME])
        for climb in find_climbs(df, params=self.__climb):
            log.info(f'Have a climb (elevation {climb[N.CLIMB_ELEVATION]})')
            self.__register_climb(s, df, climb, sector_group)

    def __find_small_climbs(self, s, sector_group, ajournal):
        log.info('Finding climbs from the remaining route')
        df = self.__non_climb_paths(s, sector_group.id, ajournal.id)
        df = expand_distance_time(df)
        df = elapsed_time_to_time(df, ajournal.start)
        df = df.set_index(df[N.TIME]).drop(columns=[N.TIME])
        for path in df['path'].unique():
            df_path = df.loc[df['path'] == path]
            for climb in find_climbs(df_path):
                log.info(f'Have a climb (elevation {climb[N.CLIMB_ELEVATION]})')
                self.__register_climb(s, df, climb, sector_group)

    def __register_climb(self, s, df, climb, sector_group):
        df = df.loc[climb[N.TIME] - dt.timedelta(seconds=climb[N.CLIMB_TIME]) : climb[N.TIME]]
        points = [f'ST_MakePoint({row.x}, {row.y})' for row in df.itertuples()]
        route = f'ST_MakeLine(ARRAY[{", ".join(points)}])'
        box = f'Box2D({route})'
        while True:
            try:
                self.__add_climb(s, sector_group, climb, route, box)
                s.commit()
                log.info('Added climb')
                return
            except IntegrityError:
                s.rollback()
                if self.__blocked_by_bigger(s, sector_group, box, climb[N.CLIMB_ELEVATION]):
                    log.info('Climb was blocked by bigger climb')
                    return
                else:
                    self.__remove_smaller(s, sector_group, box, climb[N.CLIMB_ELEVATION])

    def __blocked_by_bigger(self, s, sector_group, box, elevation):
        query = s.query(Sector). \
            join(Climb). \
            filter(Sector.sector_group == sector_group,
                   Sector.owner == self,
                   Climb.elevation >= elevation,
                   Sector.exclusion.intersects(text(box)))
        return s.query(query.exists()).scalar()

    def __remove_smaller(self, s, sector_group, box, elevation):
        query = s.query(Sector.id). \
            join(Climb). \
            filter(Sector.sector_group == sector_group,
                   Sector.owner == self,
                   Climb.elevation < elevation,
                   Sector.exclusion.intersects(text(box)))
        n = query.count()
        if n:
            log.info(f'Deleting {n} smaller climbs')
            s.query(Sector).filter(Sector.id.in_(query)).delete(synchronize_session=False)
        else:
            log.warning('Climb was blocked, but no bigger or smaller climbs exist')

    def __add_climb(self, s, sector_group, climb, route, box):
        if N.CLIMB_CATEGORY in climb:
            title = f'Climb (cat {climb[N.CLIMB_CATEGORY]})'
        else:
            title = f'Climb (uncat)'
        # text because we're passing in direct SQL functions, not EWKT
        sector = add(s, Sector(sector_group=sector_group, route=text(route), title=title,
                     owner=self, exclusion=text(box)))
        s.commit()
        category = climb.get(N.CLIMB_CATEGORY, None)
        add(s, Climb(sector=sector, category=category, elevation=climb[N.CLIMB_ELEVATION],
                     distance=climb[N.CLIMB_DISTANCE]))
        return 1

    def __complete_route(self, s, sector_group_id, activity_journal_id):
        sql = text(f'''
  with points as (select st_dumppoints(st_transform(aj.route_edt::geometry, sg.srid)) as point
                    from activity_journal as aj,
                         sector_group as sg
                   where aj.id = :activity_journal_id
                     and sg.id = :sector_group_id
                     and st_distance(sg.centre, aj.centre) < sg.radius)
select st_x((point).geom) as x, st_y((point).geom) as y, 
       st_z((point).geom) as {N.ELEVATION}, st_m((point).geom) as distance_time
  from points;
        ''')
        log.debug(sql)
        df = pd.read_sql(sql, s.connection(),
                         params={'sector_group_id': sector_group_id,
                                 'activity_journal_id': activity_journal_id})
        return df


    def __non_climb_paths(self, s, sector_group_id, activity_journal_id, buffer=20):
        sql = text(f'''
  with climbs as (select climb
                    from (select st_collect(st_buffer(st_setsrid(s.route, sg.srid), 20, 'endcap=flat')) as climb,
                                 0 as order
                            from sector as s,
                                 sector_group as sg
                           where sg.id = s.sector_group_id
                             and sg.id = :sector_group_id
                             and owner = :owner
                           union
                          select st_mlinefromtext('multilinestring empty', sg.srid),
                                 1 as order
                            from sector_group as sg
                           where sg.id = :sector_group_id) as _
                    order by "order" limit 1),
       -- this is a singleton and is carried through below so that m can be extracted
       route as (select st_transform(aj.route_edt::geometry, sg.srid) as route
                   from activity_journal as aj,
                        sector_group as sg
                  where aj.id = :activity_journal_id
                    and sg.id = :sector_group_id
                    and st_distance(sg.centre, aj.centre) < sg.radius),
       lines as (select st_dump(st_multi(st_difference(r.route, c.climb))) as line,
                        r.route as route
                   from activity_journal as aj,
                        climbs as c,
                        sector_group as sg,
                        route as r
                  where aj.id = :activity_journal_id
                    and sg.id = :sector_group_id),
       points as (select st_dumppoints((line).geom) as point,
                         route,
                         (line).path[1]
                    from lines),
       -- extract m
       og_points as (select st_lineinterpolatepoint(route, 
                                                    greatest(0, least(1, 
                                                       st_linelocatepoint(route, (point).geom)))) as point,
                            path as path
                       from points)
select st_x(point) as x, st_y(point) as y, st_z(point) as elevation, st_m(point) as distance_time, path
  from og_points;
        ''')
        log.debug(sql)
        df = pd.read_sql(sql, s.connection(),
                         params={'sector_group_id': sector_group_id,
                                 'owner': short_cls(self),
                                 'activity_journal_id': activity_journal_id,
                                 'buffer': buffer})
        return df

    def __original_route(self, s, ajournal):
        return Statistics(s, activity_journal=ajournal, with_timespan=True). \
            by_name(SegmentReader, N.DISTANCE, N.HEART_RATE, N.SPHERICAL_MERCATOR_X, N.SPHERICAL_MERCATOR_Y). \
            by_name(ElevationCalculator, N.ELEVATION).df
