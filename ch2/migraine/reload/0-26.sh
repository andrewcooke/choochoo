#!/usr/bin/env bash


# you may want to change these variables

DB_DIR=~/.ch2
TMP_DIR=/tmp

VER='0-26'

# these allow you to skip parts of the logic if re-doing a migration (expert only)
DO_COPY=1
DO_DROP=1
DO_DUMP=1


# this section of the script copies diary and kit data across

if ((DO_COPY)); then
  echo "ensuring write-ahead file for $DB_DIR/database-$VER.sql is cleared"
  echo "(should print 'delete')"
  sqlite3 "$DB_DIR/database-$VER.sql" 'pragma journal_mode=delete'
  echo "copying data to $TMP_DIR/copy-$VER.sql"
  rm -f "$DB_DIR/database-$VER.sql-backup"
  cp "$DB_DIR/database-$VER.sql" "$DB_DIR/database-$VER.sql-backup"
  rm -f "$TMP_DIR/copy-$VER.sql"
  cp "$DB_DIR/database-$VER.sql" "$TMP_DIR/copy-$VER.sql"
fi

if ((DO_DROP)); then
  echo "dropping activity data from $TMP_DIR/copy-$VER.sql"
  sqlite3 "$TMP_DIR/copy-$VER.sql" <<EOF
  pragma foreign_keys = on;
  -- don't delete topic and kit data, and keep composite for next step
  delete from source where type not in (3, 9, 10, 7);
  delete from statistic_name where id in (
    select statistic_name.id from statistic_name
      left outer join statistic_journal
        on statistic_journal.statistic_name_id = statistic_name.id
     where statistic_journal.id is null
  );
  -- clean composite data
  delete from source where id in (
    select id from (
      select composite_source.id, composite_source.n_components as target, count(composite_component.id) as actual
        from composite_source left outer join composite_component
          on composite_source.id = composite_component.output_source_id
       group by composite_component.id
    ) where target != actual
  );
EOF
fi

if ((DO_DUMP)); then
  echo "extracting data from $TMP_DIR/copy-$VER.sql to load into new database"
  rm -f "$TMP_DIR/dump-$VER.sql"
  # .commands cannot be indented?!
  sqlite3 "$TMP_DIR/copy-$VER.sql" <<EOF
.output $TMP_DIR/dump-$VER.sql
.mode insert source
select * from source;
.mode insert composite_source
select * from composite_source;
.mode insert composite_component
select * from composite_component;
.mode insert statistic_journal
select * from statistic_journal;
.mode insert statistic_journal_float
select * from statistic_journal_float;
.mode insert statistic_journal_integer
select * from statistic_journal_integer;
.mode insert statistic_journal_text
select * from statistic_journal_text;
.mode insert statistic_journal_timestamp
select * from statistic_journal_timestamp;
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
.mode insert kit_group
select * from kit_group;
.mode insert kit_item
select * from kit_item;
.mode insert kit_component
select * from kit_component;
.mode insert kit_model
select * from kit_model;
EOF
fi

echo "creating new, empty database at $DB_DIR/database-$VER.sql"
echo "(should print warning config message)"
rm -f "$DB_DIR/database-$VER.sql"
dev/ch2 no-op

echo "loading data into $DB_DIR/database-$VER.sql"
sqlite3 "$DB_DIR/database-$VER.sql" < "$TMP_DIR/dump-$VER.sql"


# you almost certainly want to change the following details

echo "adding custom data to $DB_DIR/database-$VER.sql"
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
