
from logging import getLogger

from ch2.lib.date import to_time
from ch2.squeal import ActivityBookmark
from ch2.squeal.database import connect

log = getLogger(__name__)


class CoastingBookmark:

    def __init__(self, log, db):
        self._log = log
        self._db = db

    def run(self, min_time, max_cadence, min_speed, constraint=None):
        with self._db.session_context() as s:
            self.__delete_previous(s, constraint)
            for aj_id, start, finish in self.__find(s, min_time, max_cadence, min_speed):
                self.__add(s, aj_id, start, finish, constraint)

    def __delete_previous(self, s, constraint):
        s.query(ActivityBookmark). \
            filter(ActivityBookmark.owner == self,
                   ActivityBookmark.constraint == constraint). \
            delete()

    def __add(self, s, aj_id, start, finish, constraint):
        log.info('%s - %s (%d)' % (to_time(start), to_time(finish), aj_id))
        s.add(ActivityBookmark(activity_journal_id=aj_id, start=start, finish=finish,
                               owner=self, constraint=constraint))

    def __find(self, s, min_time, max_cadence, min_speed):
        s.execute('PRAGMA automatic_index=OFF;')
        for row in s.execute('''
select a.id, s.time, f.time
  from statistic_name as c,
       statistic_name as d,
       statistic_name as v,
       activity_timespan as t cross join
       statistic_journal as s,
       statistic_journal_integer as si,
       statistic_journal as ss,
       statistic_journal_integer as ssi,
       statistic_journal as f,
       statistic_journal_integer as fi,
       statistic_journal as ff,
       statistic_journal_integer as ffi,
       activity_journal as a
 where c.name = 'Cadence'
   and d.name = 'Distance'
   and v.name = 'Speed'
   and s.statistic_name_id = c.id
   and f.statistic_name_id = c.id
   and ss.statistic_name_id = c.id
   and ff.statistic_name_id = c.id
   and s.id = si.id
   and f.id = fi.id
   and ss.id = ssi.id
   and ff.id = ffi.id
   and si.value < :max_cadence
   and fi.value < :max_cadence
   and ss.serial = s.serial-1
   and ff.serial = f.serial+1
   and s.source_id = f.source_id
   and ss.source_id = f.source_id
   and ff.source_id = f.source_id
   and ssi.value >= :max_cadence
   and ffi.value >= :max_cadence
   and f.time - s.time > :min_time
   and t.activity_journal_id = f.source_id
   and t.start < s.time
   and t.finish > f.time
   and a.id == f.source_id
   and not exists (select 1
                     from statistic_journal_integer as ji,
                          statistic_journal as j
                    where ji.value >= :max_cadence
                      and ji.id = j.id
                      and j.statistic_name_id = c.id
                      and j.source_id = s.source_id
                      and j.serial > s.serial
                      and j.serial < f.serial)
   and exists (select 1
                 from statistic_journal_float as f1,
                      statistic_journal_float as f2,
                      statistic_journal as j1,
                      statistic_journal as j2
                where f1.id = j1.id
                  and f2.id = j2.id
                  and j1.statistic_name_id = d.id
                  and j2.statistic_name_id = d.id
                  and j1.serial = s.serial
                  and j2.serial = f.serial
                  and j1.source_id = f.source_id
                  and j2.source_id = f.source_id
                  and f2.value - f1.value > :min_speed * (f.time - s.time))
   and not exists (select 1
                     from statistic_journal_float as jf,
                          statistic_journal as j
                    where jf.value = 0
                      and jf.id = j.id
                      and j.statistic_name_id = v.id
                      and j.source_id = s.source_id
                      and j.serial >= s.serial
                      and j.serial <= f.serial);
        ''', {'min_time': min_time, 'max_cadence': max_cadence, 'min_speed': min_speed}):
            yield row[0], row[1], row[2]
        s.execute('PRAGMA automatic_index=ON;')


if __name__ == '__main__':
    ns, db = connect(['-v 4'])
    CoastingBookmark(log, db).run(60, 20, 0, constraint='60/20/0')
