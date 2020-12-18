from logging import getLogger

import pandas as pd
from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape
from sqlalchemy import text, desc

from . import ContentType
from ...common.date import time_to_local_time
from ...data.sector import add_start_finish
from ...diary.model import DB
from ...names import N
from ...pipeline.process import run_pipeline
from ...sql import ActivityJournal, PipelineType, SectorJournal
from ...sql.tables.sector import SectorGroup, DEFAULT_GROUP_RADIUS_KM, SectorType
from ...sql.types import linestringxy
from ...sql.utils import WGS84_SRID, add

log = getLogger(__name__)


class ActivityBase(ContentType):

    def _read_activity_route_wkb(self, s, activity_journal_id):
        q = text(f'''
select st_force2d(aj.route_et::geometry)
  from activity_journal as aj
 where aj.id = :activity_journal_id''')
        return WKBElement(s.connection().execute(q, activity_journal_id=activity_journal_id).fetchone()[0])


class Sector(ActivityBase):

    def __init__(self, config):
        super().__init__()
        self.__config = config

    def create_sector(self, request, s):
        from ...sql import Sector
        data = request.json
        activity = data['activity']
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
        run_pipeline(self.__config, PipelineType.SECTOR, new_sector_id=sector.id)
        return {'sector': sector.id}

    def read_sector_journals(self, request, s, sector):
        from ...sql import Sector
        instance = s.query(Sector).filter(Sector.id == sector).one()
        return {'name': instance.title,
                'sector_journals': list(self.__read_sector_journals(s, sector))}

    def __read_sector_journals(self, s, sector):
        '''
        the sqlalchemy below expands into this, which gives a 5s query:

SELECT statistic_journal_text.value AS statistic_journal_text_value
  FROM statistic_journal
  JOIN statistic_journal_text ON statistic_journal.id = statistic_journal_text.id
  JOIN statistic_name ON statistic_name.id = statistic_journal.statistic_name_id
  JOIN activity_topic_field ON activity_topic_field.statistic_name_id = statistic_name.id
  JOIN activity_topic ON activity_topic.id = activity_topic_field.activity_topic_id
  JOIN (source JOIN activity_topic_journal ON source.id = activity_topic_journal.id) ON activity_topic_journal.id = statistic_journal.source_id
  JOIN (source AS source_1 JOIN activity_journal AS activity_journal_1 ON source_1.id = activity_journal_1.id) ON activity_journal_1.file_hash_id = activity_topic_journal.file_hash_id
 WHERE statistic_name.name = 'name'
   AND activity_journal_1.id = 9835
   AND activity_topic.activity_group_id = source_1.activity_group_id;

dropping the reference to source gives this, which is instantaneous.  i do not understand why.

SELECT statistic_journal_text.value AS statistic_journal_text_value
  FROM statistic_journal
  JOIN statistic_journal_text ON statistic_journal.id = statistic_journal_text.id
  JOIN statistic_name ON statistic_name.id = statistic_journal.statistic_name_id
  JOIN activity_topic_field ON activity_topic_field.statistic_name_id = statistic_name.id
  JOIN activity_topic ON activity_topic.id = activity_topic_field.activity_topic_id
  JOIN activity_topic_journal ON activity_topic_journal.id = statistic_journal.source_id
  JOIN (source AS source_1 JOIN activity_journal AS activity_journal_1 ON source_1.id = activity_journal_1.id) ON activity_journal_1.file_hash_id = activity_topic_journal.file_hash_id
 WHERE statistic_name.name = 'name'
   AND activity_journal_1.id = 9835
   AND activity_topic.activity_group_id = source_1.activity_group_id;

        '''
        for sjournal in s.query(SectorJournal). \
                filter(SectorJournal.sector_id == sector). \
                join(ActivityJournal, SectorJournal.activity_journal_id == ActivityJournal.id). \
                order_by(desc(ActivityJournal.start)).all():
            # q = s.query(StatisticJournalText.value). \
            #     join(StatisticName, StatisticName.id == StatisticJournalText.statistic_name_id). \
            #     join(ActivityTopicField, ActivityTopicField.statistic_name_id == StatisticName.id). \
            #     join(ActivityTopic, ActivityTopic.id == ActivityTopicField.activity_topic_id). \
            #     join(ActivityTopicJournal, ActivityTopicJournal.id == StatisticJournal.source_id). \
            #     join(ActivityJournal, ActivityJournal.file_hash_id == ActivityTopicJournal.file_hash_id). \
            #     filter(StatisticName.name == 'name',
            #            ActivityJournal.id == sjournal.activity_journal.id,
            #            ActivityTopic.activity_group_id == ActivityJournal.activity_group_id)
            # activity_name = q.one()[0]
            q = text('''
SELECT statistic_journal_text.value AS statistic_journal_text_value
  FROM statistic_journal
  JOIN statistic_journal_text ON statistic_journal.id = statistic_journal_text.id
  JOIN statistic_name ON statistic_name.id = statistic_journal.statistic_name_id
  JOIN activity_topic_field ON activity_topic_field.statistic_name_id = statistic_name.id
  JOIN activity_topic ON activity_topic.id = activity_topic_field.activity_topic_id
  JOIN activity_topic_journal ON activity_topic_journal.id = statistic_journal.source_id
  JOIN (source AS source_1 JOIN activity_journal AS activity_journal_1 ON source_1.id = activity_journal_1.id) ON activity_journal_1.file_hash_id = activity_topic_journal.file_hash_id
 WHERE statistic_name.name = 'name'
   AND activity_journal_1.id = :activity_journal_id
   AND activity_topic.activity_group_id = source_1.activity_group_id;
''')
            activity_name = s.connection(). \
                execute(q, activity_journal_id=sjournal.activity_journal.id). \
                fetchone()[0]
            yield {DB: sjournal.id,
                   'date': time_to_local_time(sjournal.activity_journal.start),
                   'name': activity_name,
                   'activity_group': sjournal.activity_journal.activity_group.title,
                   'activity_id': sjournal.activity_journal.id,
                   'distance': sjournal.finish_distance - sjournal.start_distance,
                   'time': (sjournal.finish_time - sjournal.start_time).total_seconds(),
                   'elevation': sjournal.finish_elevation - sjournal.start_elevation,
                   'edt': self._read_sector_journal_edt(s, sjournal.id)}

    def _read_sector_journal_edt(self, s, sector_journal_id):
        df = self._read_clipped_d_et(s, sector_journal_id)
        return {
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
