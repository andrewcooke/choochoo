#!/usr/bin/env bash


# you may want to change these directories

DB_DIR=~/.ch2
TMP_DIR=/tmp


# this section of the script copies diary data across

echo "ensuring write-ahead file for $DB_DIR/database.sqlr is cleared"
sqlite3 "$DB_DIR/database.sqlr" 'pragma journal_mode=delete'
echo "copying data to $TMP_DIR/copy.sqlr"
rm -f "$TMP_DIR/copy.sqlr"
cp "$DB_DIR/database.sqlr" "$TMP_DIR/copy.sqlr"

echo "dropping activity data from $TMP_DIR/copy.sqlr"
sqlite3 "$TMP_DIR/copy.sqlr" <<EOF
pragma foreign_keys = on;
delete from source where type != 3;
delete from statistic_name where id in (
  select statistic_name.id from statistic_name
    left outer join statistic_journal
      on statistic_journal.statistic_name_id = statistic_name.id
   where statistic_journal.id is null
);
EOF

echo "extracting data from $TMP_DIR/copy.sqlr to load into new database"
rm -f "$TMP_DIR/dump.sqlr"
sqlite3 "$TMP_DIR/copy.sqlr" <<EOF
update statistic_name set "constraint" = 'None' where "constraint" is null;
.output $TMP_DIR/dump.sqlr
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

echo "creating new, empty database at $DB_DIR/database-0-24.sql"
rm -f "$DB_DIR/database-0-24.sql"
dev/ch2 no-op

echo "loading data into $DB_DIR/database-0-24.sql"
sqlite3 "$DB_DIR/database-0-24.sql" < "$TMP_DIR/dump.sqlr"


# you almost certainly want to change the following details

echo "adding custom data to $DB_DIR/database-0-24.sql"
source env/bin/activate
python <<EOF
from ch2.config import *
from ch2.config.database import add_enum_constant
from ch2.stoats.calculate.power import Bike

db = config('-v 5')
with db.session_context() as s:
     add_enum_constant(s, 'Cotic Soul', Bike, constraint='ActivityGroup "Bike"')
EOF

dev/ch2 --dev config default --no-diary
dev/ch2 --dev constants --set FTHR.Bike 154
dev/ch2 --dev constants --set FTHR.Walk 154
dev/ch2 --dev constants --set SRTM1.Dir /home/andrew/archive/srtm1
dev/ch2 --dev constants --set 'Cotic Soul' '{"cda": 0.44, "crr": 0, "weight": 12}'



echo "next, run 'ch2 activities' or similar to load data"
