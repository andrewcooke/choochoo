from logging import getLogger

import pandas as pd
from sqlalchemy import text

from ch2.common.date import local_time_to_time
from ch2.data.climb import find_climbs
from ch2.names import N
from ch2.pipeline.calculate.elevation import expand_distance_time
from ch2.pipeline.calculate.utils import ActivityJournalCalculatorMixin, ProcessCalculator
from ch2.sql import Timestamp
from ch2.sql.database import connect_config
from ch2.sql.tables.sector import SectorGroup
from ch2.sql.types import short_cls

log = getLogger(__name__)


class ClimbCalculator(ActivityJournalCalculatorMixin, ProcessCalculator):

    def _run_one(self, missed):
        start = local_time_to_time(missed)
        with self._config.db.session_context() as s:
            ajournal = self._get_source(s, start)
            with Timestamp(owner=self.owner_out, source=ajournal).on_success(s):
                if ajournal.route_edt:
                    self.__find_new_climbs(s, ajournal)
                    self.__measure_existing_climbs(s, ajournal)

    def __measure_existing_climbs(self, s, ajournal):
        pass

    def __find_new_climbs(self, s, ajournal):
        for sector_group in s.query(SectorGroup).all():
            df = self.__non_climb_lines(s, sector_group.id, ajournal.id)
            df = expand_distance_time(df, 'distance_time', ajournal.start)
            df = df.set_index(df[N.TIME]).drop(columns=[N.TIME])
            for path in df['path'].unique():
                df_path = df.loc[df['path'] == path]
                climbs = list(find_climbs(df_path))
                if climbs:
                    print(climbs)

    def __non_climb_lines(self, s, sector_group_id, activity_journal_id, radius=20):
        sql = text(f'''
  with climbs as (select st_collect(st_buffer(route, 20, 'endcap=flat')) as climb
                    from sector
                   where sector_group_id = :sector_group_id
                     and owner = :owner
                   union
                  select st_mlinefromtext('multilinestring empty', sg.srid)
                    from sector_group as sg
                   where sg.id = :sector_group_id
                   limit 1),
       lines as (select st_dump(st_multi(st_difference(st_transform(aj.route_edt::geometry, sg.srid), c.climb))) as line
                   from activity_journal as aj,
                        climbs as c,
                        sector_group as sg
                  where aj.id = :activity_journal_id
                    and sg.id = :sector_group_id
                    and st_distance(sg.centre, aj.centre) < sg.radius),
       points as (select st_dumppoints((line).geom) as point,
                         (line).path[1]
                    from lines)
select st_x((point).geom) as x, st_y((point).geom) as y, 
       st_z((point).geom) as {N.ELEVATION}, st_m((point).geom) as distance_time, path
  from points;
        ''')
        log.debug(sql)
        df = pd.read_sql(sql, s.connection(),
                         params={'sector_group_id': sector_group_id,
                                 'owner': short_cls(self),
                                 'activity_journal_id': activity_journal_id})
        return df


if __name__ == '__main__':
    config = connect_config(['-v5'])
    ClimbCalculator(config).run()
