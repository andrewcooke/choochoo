from collections import defaultdict
from itertools import groupby
from logging import getLogger
from random import uniform

from sqlalchemy import inspect, alias, select, and_, func, text

from ch2.names import N
from ch2.pipeline.calculate.utils import RerunWhenNewActivitiesMixin, ProcessCalculator
from ch2.rtree import MatchType
from ch2.rtree.spherical import SQRTree
from ch2.sql import Timestamp, StatisticName, StatisticJournal, StatisticJournalFloat, ActivityJournal, \
    ActivityDistance

log = getLogger(__name__)


class HausdorffDistanceCalculator(ProcessCalculator):

    def __init__(self, *args, frac_len_cutoff=0.5, centre_cutoff=0.5, **kargs):
        self.frac_len_cutoff = frac_len_cutoff
        self.centre_cutoff = centre_cutoff
        super().__init__(*args, **kargs)

    def _missing(self, s):
        with self._config.db.session_context() as s:
            sql = text(f'''
  with matched as (
       select activity_journal_lo_id as id
         from activity_distance
        union
       select activity_journal_hi_id as id
         from activity_distance)
select a1.id as lo, a2.id as hi
  from activity_journal as a1, activity_journal as a2
 where a1.id < a2.id
   and a1.route_simple is not null
   and a2.route_simple is not null
   and abs(a1.distance - a2.distance) < :frac_len_cutoff * (a1.distance + a2.distance) / 2 
   and ST_Distance(a1.centre, a2.centre) < :centre_cutoff * (a1.distance + a2.distance) / 2
   and not (a1.id in (select id from matched) and a2.id in (select id from matched))
 order by a2.id, a1.id;
''')
            return [f'{row[0]}:{row[1]}'
                    for row in s.execute(sql, params={'frac_len_cutoff': self.frac_len_cutoff,
                                                      'centre_cutoff': self.centre_cutoff}).all()]

    def _run_one(self, missed):
        lo, hi = [int(x) for x in missed.split(':')]
        log.info(f'Calculating the distance between {lo} and {hi}')
        with self._config.db.session_context() as s:
            with Timestamp(owner=self.__class__).on_success(s):
                sql = text(f'''
insert into activity_distance (activity_journal_lo_id, activity_journal_hi_id, distance)
select :lo, :hi, 
       ST_HausdorffDistance(st_transform(alo.route_simple::geometry, alo.utm_srid),
                            st_transform(ahi.route_simple::geometry, alo.utm_srid))
  from activity_journal as alo,
       activity_journal as ahi
 where alo.id = :lo
   and ahi.id = :hi;
''')
                s.execute(sql, params={'lo': lo, 'hi': hi})
