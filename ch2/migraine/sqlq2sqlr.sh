#!/usr/bin/env bash

cat > /dev/null <<XXX

sqlite3 ~/.ch2/database.sqlq 'pragma journal_mode=delete'
rm -f /tmp/copy.sqlq
cp ~/.ch2/database.sqlq /tmp/copy.sqlq

sqlite3 /tmp/copy.sqlq <<EOF
pragma foreign_keys = on;
delete from source where type != 3;
delete from statistic_name where id in (
  select statistic_name.id from statistic_name
    left outer join statistic_journal
      on statistic_journal.statistic_name_id = statistic_name.id
   where statistic_journal.id is null
);
alter table statistic_name add column statistic_journal_type integer default 2;
update statistic_name set statistic_journal_type=3 where summary='[cnt]';
update statistic_name set statistic_journal_type=1 where name in ('Mood', 'Rest HR');
EOF

rm -f /tmp/dump-q.sql
sqlite3 /tmp/copy.sqlq <<EOF
update statistic_name set "constraint" = 'None' where "constraint" is null;
.output /tmp/dump-q.sql
.mode insert source
select * from source;
.mode insert statistic_journal
select * from statistic_journal;
.mode insert statistic_journal_float
select * from statistic_journal_float;
.mode insert statistic_journal_integer
select * from statistic_journal_integer;
.mode insert statistic_journal_text
select * from statistic_journal_text;
.mode insert statistic_name
select * from statistic_name;
.mode insert topic
select * from topic;
.mode insert topic_field
select * from topic_field;
.mode insert topic_journal
select * from topic_journal;
.mode insert segment
select * from segment;
EOF

XXX

rm -f ~/.ch2/database.sqlr
dev/ch2 no-op

sqlite3 ~/.ch2/database.sqlr < /tmp/dump-q.sql

source env/bin/activate
python <<EOF
from ch2.config import *
from ch2.config.database import add_enum_constant
from ch2.stoats.calculate.power import Bike

db = config('-v 5')
with db.session_context() as s:
     add_enum_constant(s, 'Cotic Soul', Bike, constraint='ActivityGroup "Bike"')
EOF

dev/ch2 --dev default-config --no-diary
dev/ch2 --dev constants --set FTHR.Bike 154
dev/ch2 --dev constants --set SRTM1.Dir /home/andrew/archive/srtm1
dev/ch2 --dev constants --set 'Cotic Soul' '{"cda": 0.44, "crr": 0, "weight": 12}'
