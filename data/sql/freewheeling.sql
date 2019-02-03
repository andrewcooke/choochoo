
select f.time - s.time as delta,
       s.time as start,
       f.time as finish,
       f.source_id as activity_id
  from statistic_journal as s,
       statistic_journal_integer as si,
       statistic_journal as f,
       statistic_journal_integer as fi,
       statistic_name as c,
       statistic_name as v
 where c.name = 'Cadence'
   and v.name = 'Speed'
   and s.statistic_name_id = c.id
   and f.statistic_name_id = c.id
   and s.id = si.id
   and f.id = fi.id
   and si.value = 0
   and fi.value = 0
   and s.source_id = f.source_id
   and f.time >= s.time + 30
   and not exists (select 1
                     from statistic_journal_integer as i,
                          statistic_journal as j
                    where i.value != 0
                      and i.id = j.id
                      and j.statistic_name_id = c.id
                      and j.source_id = s.source_id
                      and j.time > s.time
                      and j.time < f.time)
   and not exists (select 1
                     from statistic_journal_float as f,
                          statistic_journal as j
                    where f.value = 0
                      and f.id = j.id
                      and j.statistic_name_id = v.id
                      and j.source_id = s.source_id
                      and j.time > s.time
                      and j.time < f.time)
   and exists (select 1
                 from statistic_journal_float as f,
                      statistic_journal as j
                where f.value > 0
                  and f.id = j.id
                  and j.statistic_name_id = v.id
                  and j.source_id = s.source_id
                  and j.time > s.time
                  and j.time < f.time)
   and exists (select 1
                from activity_timespan as t
               where t.start <= s.time
                 and t.finish >= f.time);
 order by delta desc;
 
select f.time - s.time as delta,
       s.time as start,
       f.time as finish,
       f.source_id as activity_id,
       a.name
  from statistic_journal as s,
       statistic_journal_integer as si,
       statistic_journal as f,
       statistic_journal_integer as fi,
       statistic_name as c,
       statistic_name as d,
       statistic_name as v,
       activity_journal as a
 where c.name = 'Cadence'
   and d.name = 'Distance'
   and v.name = 'Speed'
   and s.statistic_name_id = c.id
   and f.statistic_name_id = c.id
   and s.id = si.id
   and f.id = fi.id
   and si.value < 20
   and fi.value < 20
   and s.source_id = f.source_id
   and delta > 60
   and a.id == f.source_id
   and not exists (select 1
                     from statistic_journal_integer as i,
                          statistic_journal as j
                    where i.value >= 20
                      and i.id = j.id
                      and j.statistic_name_id = c.id
                      and j.source_id = s.source_id
                      and j.time > s.time
                      and j.time < f.time)
   and exists (select 1
                 from statistic_journal_float as f1,
                      statistic_journal_float as f2,
                      statistic_journal as j1,
                      statistic_journal as j2
                where f1.id = j1.id
                  and f2.id = j2.id
                  and j1.statistic_name_id = d.id
                  and j2.statistic_name_id = d.id
		  and j1.time = s.time
		  and j2.time = f.time
		  and f2.value - f1.value > 3 * delta)
   and not exists (select 1
                     from statistic_journal_float as f,
                          statistic_journal as j
                    where f.value = 0
                      and f.id = j.id
                      and j.statistic_name_id = v.id
                      and j.source_id = s.source_id
                      and j.time > s.time
                      and j.time < f.time)
   and exists (select 1
                 from statistic_journal_float as f,
                      statistic_journal as j
                where f.value > 0
                  and f.id = j.id
                  and j.statistic_name_id = v.id
                  and j.source_id = s.source_id
                  and j.time > s.time
                  and j.time < f.time)
   and exists (select 1
                from activity_timespan as t
               where t.start <= s.time
                 and t.finish >= f.time)
 order by delta desc;
                  
select f.time - s.time as delta,
       s.time as start,
       f.time as finish,
       f.source_id as activity_id,
       a.name
  from statistic_journal as s,
       statistic_journal_integer as si,
       statistic_journal as ss,
       statistic_journal_integer as ssi,
       statistic_journal as f,
       statistic_journal_integer as fi,
       statistic_journal as ff,
       statistic_journal_integer as ffi,
       statistic_name as c,
       statistic_name as d,
       statistic_name as v,
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
   and si.value < 20
   and fi.value < 20
   and ss.serial = s.serial-1
   and ff.serial = f.serial+1
   and s.source_id = f.source_id
   and ss.source_id = f.source_id
   and ff.source_id = f.source_id
   and ssi.value >= 20
   and ffi.value >= 20
   and delta > 30
   and a.id == f.source_id
   and not exists (select 1
                     from statistic_journal_integer as ji,
                          statistic_journal as j
                    where ji.value >= 20
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
		  and f2.value - f1.value > 3 * delta)
   and not exists (select 1
                     from statistic_journal_float as jf,
                          statistic_journal as j
                    where jf.value = 0
                      and jf.id = j.id
                      and j.statistic_name_id = v.id
                      and j.source_id = s.source_id
                      and j.time > s.time
                      and j.time < f.time)
   and exists (select 1
                from activity_timespan as t
               where t.start <= s.time
                 and t.finish >= f.time);
                
   
0|0|8|SEARCH TABLE statistic_name AS c USING COVERING INDEX ix_statistic_name_name (name=?)
0|1|4|SEARCH TABLE statistic_journal AS f USING INDEX ix_statistic_journal_statistic_name_id (statistic_name_id=?)
0|2|6|SEARCH TABLE statistic_journal AS ff USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|3|5|SEARCH TABLE statistic_journal_integer AS fi USING INTEGER PRIMARY KEY (rowid=?)
0|4|11|SEARCH TABLE activity_journal AS a USING INTEGER PRIMARY KEY (rowid=?)
0|5|7|SEARCH TABLE statistic_journal_integer AS ffi USING INTEGER PRIMARY KEY (rowid=?)
0|6|0|SEARCH TABLE statistic_journal AS s USING INDEX ix_statistic_journal_source_id (source_id=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 1
1|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
1|1|0|SEARCH TABLE statistic_journal_integer AS i USING INTEGER PRIMARY KEY (rowid=?)
0|7|1|SEARCH TABLE statistic_journal_integer AS si USING INTEGER PRIMARY KEY (rowid=?)
0|8|2|SEARCH TABLE statistic_journal AS ss USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|9|3|SEARCH TABLE statistic_journal_integer AS ssi USING INTEGER PRIMARY KEY (rowid=?)
0|10|9|SEARCH TABLE statistic_name AS d USING COVERING INDEX ix_statistic_name_name (name=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 2
2|0|2|SEARCH TABLE statistic_journal AS j1 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|1|3|SEARCH TABLE statistic_journal AS j2 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|2|0|SEARCH TABLE statistic_journal_float AS f1 USING INTEGER PRIMARY KEY (rowid=?)
2|3|1|SEARCH TABLE statistic_journal_float AS f2 USING INTEGER PRIMARY KEY (rowid=?)
0|11|10|SEARCH TABLE statistic_name AS v USING COVERING INDEX ix_statistic_name_name (name=?)


PRAGMA foreign_keys=ON;
PRAGMA temp_store=MEMORY;
PRAGMA threads=4;

select f.time - s.time as delta,
       s.time as start,
       f.time as finish,
       f.source_id as activity_id,
       a.name
  from statistic_journal as s,
       statistic_journal_integer as si,
       statistic_journal as ss,
       statistic_journal_integer as ssi,
       statistic_journal as f,
       statistic_journal_integer as fi,
       statistic_journal as ff,
       statistic_journal_integer as ffi,
       statistic_name as c,
       statistic_name as d,
       statistic_name as v,
       activity_journal as a,
       activity_timespan as t
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
   and si.value < 20
   and fi.value < 20
   and ss.serial = s.serial-1
   and ff.serial = f.serial+1
   and s.source_id = f.source_id
   and ss.source_id = f.source_id
   and ff.source_id = f.source_id
   and ssi.value >= 20
   and ffi.value >= 20
   and delta > 30
   and t.activity_journal_id = f.source_id
   and t.start <= ss.time
   and t.finish >= ff.time
   and a.id == f.source_id
   and not exists (select 1
                     from statistic_journal_integer as ji,
                          statistic_journal as j
                    where ji.value >= 20
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
		  and f2.value - f1.value > 3 * delta)
   and not exists (select 1
                     from statistic_journal_float as jf,
                          statistic_journal as j
                    where jf.value = 0
                      and jf.id = j.id
                      and j.statistic_name_id = v.id
                      and j.source_id = s.source_id
                      and j.serial >= s.serial
                      and j.serial <= f.serial);

0|0|8|SEARCH TABLE statistic_name AS c USING COVERING INDEX ix_statistic_name_name (name=?)
0|1|4|SEARCH TABLE statistic_journal AS f USING INDEX ix_statistic_journal_statistic_name_id (statistic_name_id=?)
0|2|6|SEARCH TABLE statistic_journal AS ff USING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|3|5|SEARCH TABLE statistic_journal_integer AS fi USING INTEGER PRIMARY KEY (rowid=?)
0|4|11|SEARCH TABLE activity_journal AS a USING INTEGER PRIMARY KEY (rowid=?)
0|5|7|SEARCH TABLE statistic_journal_integer AS ffi USING INTEGER PRIMARY KEY (rowid=?)
0|6|0|SEARCH TABLE statistic_journal AS s USING INDEX ix_statistic_journal_source_id (source_id=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 1
1|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
1|1|0|SEARCH TABLE statistic_journal_integer AS ji USING INTEGER PRIMARY KEY (rowid=?)
0|7|2|SEARCH TABLE statistic_journal AS ss USING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|8|1|SEARCH TABLE statistic_journal_integer AS si USING INTEGER PRIMARY KEY (rowid=?)
0|9|3|SEARCH TABLE statistic_journal_integer AS ssi USING INTEGER PRIMARY KEY (rowid=?)
0|10|12|SEARCH TABLE activity_timespan AS t USING INDEX sqlite_autoindex_activity_timespan_1 (activity_journal_id=? AND start<?)
0|11|9|SEARCH TABLE statistic_name AS d USING COVERING INDEX ix_statistic_name_name (name=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 2
2|0|2|SEARCH TABLE statistic_journal AS j1 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|1|3|SEARCH TABLE statistic_journal AS j2 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|2|0|SEARCH TABLE statistic_journal_float AS f1 USING INTEGER PRIMARY KEY (rowid=?)
2|3|1|SEARCH TABLE statistic_journal_float AS f2 USING INTEGER PRIMARY KEY (rowid=?)
0|12|10|SEARCH TABLE statistic_name AS v USING COVERING INDEX ix_statistic_name_name (name=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 3
3|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
3|1|0|SEARCH TABLE statistic_journal_float AS jf USING INTEGER PRIMARY KEY (rowid=?)

0|0|8|SEARCH TABLE statistic_name AS c USING COVERING INDEX ix_statistic_name_name (name=?)
0|1|9|SEARCH TABLE statistic_name AS d USING COVERING INDEX ix_statistic_name_name (name=?)
0|2|10|SEARCH TABLE statistic_name AS v USING COVERING INDEX ix_statistic_name_name (name=?)
0|3|4|SEARCH TABLE statistic_journal AS f USING INDEX ix_statistic_journal_statistic_name_id (statistic_name_id=?)
0|4|11|SEARCH TABLE activity_journal AS a USING INTEGER PRIMARY KEY (rowid=?)
0|5|5|SEARCH TABLE statistic_journal_integer AS fi USING INTEGER PRIMARY KEY (rowid=?)
0|6|6|SEARCH TABLE statistic_journal AS ff USING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|7|7|SEARCH TABLE statistic_journal_integer AS ffi USING INTEGER PRIMARY KEY (rowid=?)
0|8|0|SEARCH TABLE statistic_journal AS s USING INDEX ix_statistic_journal_source_id (source_id=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 1
1|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
1|1|0|SEARCH TABLE statistic_journal_integer AS ji USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 2
2|0|2|SEARCH TABLE statistic_journal AS j1 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|1|0|SEARCH TABLE statistic_journal_float AS f1 USING INTEGER PRIMARY KEY (rowid=?)
2|2|3|SEARCH TABLE statistic_journal AS j2 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|3|1|SEARCH TABLE statistic_journal_float AS f2 USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 3
3|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
3|1|0|SEARCH TABLE statistic_journal_float AS jf USING INTEGER PRIMARY KEY (rowid=?)
0|9|1|SEARCH TABLE statistic_journal_integer AS si USING INTEGER PRIMARY KEY (rowid=?)
0|10|2|SEARCH TABLE statistic_journal AS ss USING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|11|3|SEARCH TABLE statistic_journal_integer AS ssi USING INTEGER PRIMARY KEY (rowid=?)
0|12|12|SEARCH TABLE activity_timespan AS t USING INDEX sqlite_autoindex_activity_timespan_1 (activity_journal_id=? AND start<?)


PRAGMA foreign_keys=ON;
PRAGMA temp_store=MEMORY;
PRAGMA threads=4;
PRAGMA cache_size=-1000000;
PRAGMA wal_checkpoint(FULL);

select f.time - s.time as delta,
       s.time as start,
       f.time as finish,
       f.source_id as activity_id,
       a.name
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
   and si.value < 20
   and fi.value < 20
   and ss.serial = s.serial-1
   and ff.serial = f.serial+1
   and s.source_id = f.source_id
   and ss.source_id = f.source_id
   and ff.source_id = f.source_id
   and ssi.value >= 20
   and ffi.value >= 20
   and delta > 30
   and t.activity_journal_id = f.source_id
   and t.start < s.time
   and t.finish > f.time
   and a.id == f.source_id
   and not exists (select 1
                     from statistic_journal_integer as ji,
                          statistic_journal as j
                    where ji.value >= 20
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
		  and f2.value - f1.value > 3 * delta)
   and not exists (select 1
                     from statistic_journal_float as jf,
                          statistic_journal as j
                    where jf.value = 0
                      and jf.id = j.id
                      and j.statistic_name_id = v.id
                      and j.source_id = s.source_id
                      and j.serial >= s.serial
                      and j.serial <= f.serial);

0|0|0|SEARCH TABLE statistic_name AS c USING COVERING INDEX ix_statistic_name_name (name=?)
0|1|1|SEARCH TABLE statistic_name AS d USING COVERING INDEX ix_statistic_name_name (name=?)
0|2|2|SEARCH TABLE statistic_name AS v USING COVERING INDEX ix_statistic_name_name (name=?)
0|3|3|SCAN TABLE activity_timespan AS t
0|4|4|SEARCH TABLE statistic_journal AS s USING INDEX ix_statistic_journal_source_id (source_id=?)
0|5|5|SEARCH TABLE statistic_journal_integer AS si USING INTEGER PRIMARY KEY (rowid=?)
0|6|12|SEARCH TABLE activity_journal AS a USING INTEGER PRIMARY KEY (rowid=?)
0|7|6|SEARCH TABLE statistic_journal AS ss USING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|8|7|SEARCH TABLE statistic_journal_integer AS ssi USING INTEGER PRIMARY KEY (rowid=?)
0|9|8|SEARCH TABLE statistic_journal AS f USING INDEX ix_statistic_journal_source_id (source_id=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 1
1|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
1|1|0|SEARCH TABLE statistic_journal_integer AS ji USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 2
2|0|2|SEARCH TABLE statistic_journal AS j1 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|1|0|SEARCH TABLE statistic_journal_float AS f1 USING INTEGER PRIMARY KEY (rowid=?)
2|2|3|SEARCH TABLE statistic_journal AS j2 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|3|1|SEARCH TABLE statistic_journal_float AS f2 USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 3
3|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
3|1|0|SEARCH TABLE statistic_journal_float AS jf USING INTEGER PRIMARY KEY (rowid=?)
0|10|9|SEARCH TABLE statistic_journal_integer AS fi USING INTEGER PRIMARY KEY (rowid=?)
0|11|10|SEARCH TABLE statistic_journal AS ff USING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|12|11|SEARCH TABLE statistic_journal_integer AS ffi USING INTEGER PRIMARY KEY (rowid=?)



0|0|0|SEARCH TABLE statistic_name AS c USING COVERING INDEX ix_statistic_name_name (name=?)
0|1|1|SEARCH TABLE statistic_name AS d USING COVERING INDEX ix_statistic_name_name (name=?)
0|2|2|SEARCH TABLE statistic_name AS v USING COVERING INDEX ix_statistic_name_name (name=?)
0|3|3|SCAN TABLE activity_timespan AS t
0|4|4|SEARCH TABLE statistic_journal AS s USING INDEX ix_statistic_journal_source_id (source_id=?)
0|5|6|SEARCH TABLE statistic_journal AS ss USING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|6|5|SEARCH TABLE statistic_journal_integer AS si USING INTEGER PRIMARY KEY (rowid=?)
0|7|7|SEARCH TABLE statistic_journal_integer AS ssi USING INTEGER PRIMARY KEY (rowid=?)
0|8|8|SEARCH TABLE statistic_journal AS f USING INDEX ix_statistic_journal_source_id (source_id=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 1
1|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
1|1|0|SEARCH TABLE statistic_journal_integer AS ji USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 2
2|0|2|SEARCH TABLE statistic_journal AS j1 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|1|3|SEARCH TABLE statistic_journal AS j2 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|2|0|SEARCH TABLE statistic_journal_float AS f1 USING INTEGER PRIMARY KEY (rowid=?)
2|3|1|SEARCH TABLE statistic_journal_float AS f2 USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 3
3|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
3|1|0|SEARCH TABLE statistic_journal_float AS jf USING INTEGER PRIMARY KEY (rowid=?)
0|9|10|SEARCH TABLE statistic_journal AS ff USING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|10|9|SEARCH TABLE statistic_journal_integer AS fi USING INTEGER PRIMARY KEY (rowid=?)
0|11|11|SEARCH TABLE statistic_journal_integer AS ffi USING INTEGER PRIMARY KEY (rowid=?)
0|12|12|SEARCH TABLE activity_journal AS a USING INTEGER PRIMARY KEY (rowid=?)


0|0|0|SEARCH TABLE statistic_name AS c USING COVERING INDEX ix_statistic_name_name (name=?)
0|1|1|SEARCH TABLE statistic_name AS d USING COVERING INDEX ix_statistic_name_name (name=?)
0|2|2|SEARCH TABLE statistic_name AS v USING COVERING INDEX ix_statistic_name_name (name=?)
0|3|3|SCAN TABLE activity_timespan AS t
0|4|4|SEARCH TABLE statistic_journal AS s USING INDEX from_activity_timespan (source_id=? AND time>?)
0|5|5|SEARCH TABLE statistic_journal_integer AS si USING INTEGER PRIMARY KEY (rowid=?)
0|6|6|SEARCH TABLE statistic_journal AS ss USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|7|7|SEARCH TABLE statistic_journal_integer AS ssi USING INTEGER PRIMARY KEY (rowid=?)
0|8|8|SEARCH TABLE statistic_journal AS f USING INDEX from_activity_timespan (source_id=? AND time<?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 1
1|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
1|1|0|SEARCH TABLE statistic_journal_integer AS ji USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 2
2|0|2|SEARCH TABLE statistic_journal AS j1 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|1|3|SEARCH TABLE statistic_journal AS j2 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|2|0|SEARCH TABLE statistic_journal_float AS f1 USING INTEGER PRIMARY KEY (rowid=?)
2|3|1|SEARCH TABLE statistic_journal_float AS f2 USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 3
3|0|1|SEARCH TABLE statistic_journal AS j USING INDEX ix_statistic_journal_source_id (source_id=?)
3|1|0|SEARCH TABLE statistic_journal_float AS jf USING INTEGER PRIMARY KEY (rowid=?)
0|9|10|SEARCH TABLE statistic_journal AS ff USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|10|9|SEARCH TABLE statistic_journal_integer AS fi USING INTEGER PRIMARY KEY (rowid=?)
0|11|11|SEARCH TABLE statistic_journal_integer AS ffi USING INTEGER PRIMARY KEY (rowid=?)
0|12|12|SEARCH TABLE activity_journal AS a USING INTEGER PRIMARY KEY (rowid=?)


0|0|8|SEARCH TABLE statistic_name AS c USING COVERING INDEX ix_statistic_name_name (name=?)
0|1|9|SEARCH TABLE statistic_name AS d USING COVERING INDEX ix_statistic_name_name (name=?)
0|2|11|SCAN TABLE activity_journal AS a USING COVERING INDEX sqlite_autoindex_activity_journal_1
0|3|4|SEARCH TABLE statistic_journal AS f USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
0|4|5|SEARCH TABLE statistic_journal_integer AS fi USING INTEGER PRIMARY KEY (rowid=?)
0|5|6|SEARCH TABLE statistic_journal AS ff USING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|6|7|SEARCH TABLE statistic_journal_integer AS ffi USING INTEGER PRIMARY KEY (rowid=?)
0|7|10|SEARCH TABLE statistic_name AS v USING COVERING INDEX ix_statistic_name_name (name=?)
0|8|0|SEARCH TABLE statistic_journal AS s USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 1
1|0|1|SEARCH TABLE statistic_journal AS j USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
1|1|0|SEARCH TABLE statistic_journal_integer AS ji USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 2
2|0|2|SEARCH TABLE statistic_journal AS j1 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|1|3|SEARCH TABLE statistic_journal AS j2 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|2|0|SEARCH TABLE statistic_journal_float AS f1 USING INTEGER PRIMARY KEY (rowid=?)
2|3|1|SEARCH TABLE statistic_journal_float AS f2 USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 3
3|0|1|SEARCH TABLE statistic_journal AS j USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
3|1|0|SEARCH TABLE statistic_journal_float AS jf USING INTEGER PRIMARY KEY (rowid=?)
0|9|2|SEARCH TABLE statistic_journal AS ss USING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|10|1|SEARCH TABLE statistic_journal_integer AS si USING INTEGER PRIMARY KEY (rowid=?)
0|11|3|SEARCH TABLE statistic_journal_integer AS ssi USING INTEGER PRIMARY KEY (rowid=?)
0|12|12|SEARCH TABLE activity_timespan AS t USING INDEX sqlite_autoindex_activity_timespan_1 (activity_journal_id=? AND start<?)

PRAGMA automatic_index=OFF;

0|0|0|SEARCH TABLE statistic_name AS c USING COVERING INDEX ix_statistic_name_name (name=?)
0|1|1|SEARCH TABLE statistic_name AS d USING COVERING INDEX ix_statistic_name_name (name=?)
0|2|2|SEARCH TABLE statistic_name AS v USING COVERING INDEX ix_statistic_name_name (name=?)
0|3|3|SCAN TABLE activity_timespan AS t
0|4|4|SEARCH TABLE statistic_journal AS s USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=? AND time>?)
0|5|5|SEARCH TABLE statistic_journal_integer AS si USING INTEGER PRIMARY KEY (rowid=?)
0|6|6|SEARCH TABLE statistic_journal AS ss USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|7|7|SEARCH TABLE statistic_journal_integer AS ssi USING INTEGER PRIMARY KEY (rowid=?)
0|8|8|SEARCH TABLE statistic_journal AS f USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=? AND time<?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 1
1|0|1|SEARCH TABLE statistic_journal AS j USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
1|1|0|SEARCH TABLE statistic_journal_integer AS ji USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 2
2|0|2|SEARCH TABLE statistic_journal AS j1 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|1|3|SEARCH TABLE statistic_journal AS j2 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
2|2|0|SEARCH TABLE statistic_journal_float AS f1 USING INTEGER PRIMARY KEY (rowid=?)
2|3|1|SEARCH TABLE statistic_journal_float AS f2 USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 3
3|0|1|SEARCH TABLE statistic_journal AS j USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
3|1|0|SEARCH TABLE statistic_journal_float AS jf USING INTEGER PRIMARY KEY (rowid=?)
0|9|10|SEARCH TABLE statistic_journal AS ff USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|10|9|SEARCH TABLE statistic_journal_integer AS fi USING INTEGER PRIMARY KEY (rowid=?)
0|11|11|SEARCH TABLE statistic_journal_integer AS ffi USING INTEGER PRIMARY KEY (rowid=?)
0|12|12|SEARCH TABLE activity_journal AS a USING INTEGER PRIMARY KEY (rowid=?)


select f.time - s.time as delta,
       s.time as start,
       f.time as finish,
       f.source_id as activity_id,
       a.name
  from statistic_name as c,
       statistic_name as d,
       statistic_name as v,
       activity_timespan as t,
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
   and si.value < 20
   and fi.value < 20
   and ss.serial = s.serial-1
   and ff.serial = f.serial+1
   and s.source_id = f.source_id
   and ss.source_id = f.source_id
   and ff.source_id = f.source_id
   and ssi.value >= 20
   and ffi.value >= 20
   and delta > 30
   and t.activity_journal_id = f.source_id
   and t.start < s.time
   and t.finish > f.time
   and a.id == f.source_id
   and not exists (select 1
                     from statistic_journal_integer as ji,
                          statistic_journal as j
                    where ji.value >= 20
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
		  and f2.value - f1.value > 3 * delta)
   and not exists (select 1
                     from statistic_journal_float as jf,
                          statistic_journal as j
                    where jf.value = 0
                      and jf.id = j.id
                      and j.statistic_name_id = v.id
                      and j.source_id = s.source_id
                      and j.serial >= s.serial
                      and j.serial <= f.serial);

0|0|0|SEARCH TABLE statistic_name AS c USING COVERING INDEX ix_statistic_name_name (name=?)
0|1|2|SEARCH TABLE statistic_name AS v USING COVERING INDEX ix_statistic_name_name (name=?)
0|2|12|SCAN TABLE activity_journal AS a USING COVERING INDEX sqlite_autoindex_activity_journal_1
0|3|4|SEARCH TABLE statistic_journal AS s USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
0|4|5|SEARCH TABLE statistic_journal_integer AS si USING INTEGER PRIMARY KEY (rowid=?)
0|5|6|SEARCH TABLE statistic_journal AS ss USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|6|7|SEARCH TABLE statistic_journal_integer AS ssi USING INTEGER PRIMARY KEY (rowid=?)
0|7|8|SEARCH TABLE statistic_journal AS f USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 1
1|0|1|SEARCH TABLE statistic_journal AS j USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
1|1|0|SEARCH TABLE statistic_journal_integer AS ji USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 2
2|0|1|SEARCH TABLE statistic_journal AS j USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
2|1|0|SEARCH TABLE statistic_journal_float AS jf USING INTEGER PRIMARY KEY (rowid=?)
0|8|10|SEARCH TABLE statistic_journal AS ff USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|9|11|SEARCH TABLE statistic_journal_integer AS ffi USING INTEGER PRIMARY KEY (rowid=?)
0|10|9|SEARCH TABLE statistic_journal_integer AS fi USING INTEGER PRIMARY KEY (rowid=?)
0|11|1|SEARCH TABLE statistic_name AS d USING COVERING INDEX ix_statistic_name_name (name=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 3
3|0|2|SEARCH TABLE statistic_journal AS j1 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
3|1|3|SEARCH TABLE statistic_journal AS j2 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
3|2|0|SEARCH TABLE statistic_journal_float AS f1 USING INTEGER PRIMARY KEY (rowid=?)
3|3|1|SEARCH TABLE statistic_journal_float AS f2 USING INTEGER PRIMARY KEY (rowid=?)
0|12|3|SEARCH TABLE activity_timespan AS t USING INDEX sqlite_autoindex_activity_timespan_1 (activity_journal_id=? AND start<?)

PRAGMA automatic_index=OFF;

0|0|0|SEARCH TABLE statistic_name AS c USING COVERING INDEX ix_statistic_name_name (name=?)
0|1|2|SEARCH TABLE statistic_name AS v USING COVERING INDEX ix_statistic_name_name (name=?)
0|2|12|SCAN TABLE activity_journal AS a USING COVERING INDEX sqlite_autoindex_activity_journal_1
0|3|4|SEARCH TABLE statistic_journal AS s USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
0|4|5|SEARCH TABLE statistic_journal_integer AS si USING INTEGER PRIMARY KEY (rowid=?)
0|5|6|SEARCH TABLE statistic_journal AS ss USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|6|7|SEARCH TABLE statistic_journal_integer AS ssi USING INTEGER PRIMARY KEY (rowid=?)
0|7|8|SEARCH TABLE statistic_journal AS f USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 1
1|0|1|SEARCH TABLE statistic_journal AS j USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
1|1|0|SEARCH TABLE statistic_journal_integer AS ji USING INTEGER PRIMARY KEY (rowid=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 2
2|0|1|SEARCH TABLE statistic_journal AS j USING INDEX from_activity_timespan (source_id=? AND statistic_name_id=?)
2|1|0|SEARCH TABLE statistic_journal_float AS jf USING INTEGER PRIMARY KEY (rowid=?)
0|8|10|SEARCH TABLE statistic_journal AS ff USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
0|9|11|SEARCH TABLE statistic_journal_integer AS ffi USING INTEGER PRIMARY KEY (rowid=?)
0|10|9|SEARCH TABLE statistic_journal_integer AS fi USING INTEGER PRIMARY KEY (rowid=?)
0|11|1|SEARCH TABLE statistic_name AS d USING COVERING INDEX ix_statistic_name_name (name=?)
0|0|0|EXECUTE CORRELATED SCALAR SUBQUERY 3
3|0|2|SEARCH TABLE statistic_journal AS j1 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
3|1|3|SEARCH TABLE statistic_journal AS j2 USING COVERING INDEX sqlite_autoindex_statistic_journal_2 (serial=? AND source_id=? AND statistic_name_id=?)
3|2|0|SEARCH TABLE statistic_journal_float AS f1 USING INTEGER PRIMARY KEY (rowid=?)
3|3|1|SEARCH TABLE statistic_journal_float AS f2 USING INTEGER PRIMARY KEY (rowid=?)
0|12|3|SEARCH TABLE activity_timespan AS t USING INDEX sqlite_autoindex_activity_timespan_1 (activity_journal_id=? AND start<?)



PRAGMA automatic_index=OFF;

select f.time - s.time as delta,
       s.time as start,
       f.time as finish,
       f.source_id as activity_id,
       a.name
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
   and si.value < 20
   and fi.value < 20
   and ss.serial = s.serial-1
   and ff.serial = f.serial+1
   and s.source_id = f.source_id
   and ss.source_id = f.source_id
   and ff.source_id = f.source_id
   and ssi.value >= 20
   and ffi.value >= 20
   and delta > 30
   and t.activity_journal_id = f.source_id
   and t.start < s.time
   and t.finish > f.time
   and a.id == f.source_id
   and not exists (select 1
                     from statistic_journal_integer as ji,
                          statistic_journal as j
                    where ji.value >= 20
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
		  and f2.value - f1.value > 3 * delta)
   and not exists (select 1
                     from statistic_journal_float as jf,
                          statistic_journal as j
                    where jf.value = 0
                      and jf.id = j.id
                      and j.statistic_name_id = v.id
                      and j.source_id = s.source_id
                      and j.serial >= s.serial
                      and j.serial <= f.serial);
