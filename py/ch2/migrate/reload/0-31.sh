#!/usr/bin/env bash

# there are more things to edit at the end of this file

# you may want to change these variables

DB_DIR=~/.ch2
TMP_DIR=/tmp

VER='0-31'

# these allow you to skip parts of the logic if re-doing a migration (expert only)
DO_COPY=1
DO_DROP=1
DO_DUMP=1


# this section of the script copies diary and kit data across

if ((DO_COPY)); then
  echo "ensuring write-ahead file for $DB_DIR/database-$VER.db is cleared"
  echo "(should print 'delete')"
  sqlite3 "$DB_DIR/database-$VER.db" 'pragma journal_mode=delete' || { fuser "$DB_DIR/database-$VER.db"; exit 1; }
  echo "copying $DB_DIR/database-$VER.db to $TMP_DIR/copy-$VER.db"
  rm -f "$DB_DIR/database-$VER-backup.db"
  cp "$DB_DIR/database-$VER.db" "$DB_DIR/database-$VER-backup.db"
  rm -f "$TMP_DIR/copy-$VER.db"
  cp "$DB_DIR/database-$VER.db" "$TMP_DIR/copy-$VER.db"
fi

if ((DO_DROP)); then
  echo "dropping activity data from $TMP_DIR/copy-$VER.db"
  sqlite3 "$TMP_DIR/copy-$VER.db" <<EOF
  pragma foreign_keys = on;
  -- don't delete topic and kit data, and keep composite for next step
  delete from source where type not in (3, 9, 10, 7, 11);
  delete from statistic_name where id in (
    select statistic_name.id from statistic_name
      left outer join statistic_journal
        on statistic_journal.statistic_name_id = statistic_name.id
     where statistic_journal.id is null
       and statistic_name.owner not in ('DiaryTopic', 'ActivityTopic')
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
  delete from source where id in (
    select id from composite_source where n_components = 0
  );
  -- remove statistic names used by constants
  delete from statistic_name where owner = 'Constant';
EOF
fi

if ((DO_DUMP)); then
  echo "extracting data from $TMP_DIR/copy-$VER.db to load into new database"
  rm -f "$TMP_DIR/dump-$VER.db"
  # .commands cannot be indented?!
  sqlite3 "$TMP_DIR/copy-$VER.db" <<EOF
.output $TMP_DIR/dump-$VER.db
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
.mode insert diary_topic
select * from diary_topic;
.mode insert diary_topic_field
select * from diary_topic_field;
.mode insert diary_topic_journal
select * from diary_topic_journal;
.mode insert activity_topic
select * from activity_topic;
.mode insert activity_topic_field
select * from activity_topic_field;
.mode insert activity_topic_journal
select * from activity_topic_journal;
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
.mode insert file_hash
select * from file_hash;
EOF
fi

echo "creating new, empty database at $DB_DIR/database-$VER.db"
echo "(should print warning config message)"
rm -f "$DB_DIR/database-$VER.db"
rm -f "$DB_DIR/database-$DST.db-shm"
rm -f "$DB_DIR/database-$DST.db-wal"
rm -f "$DB_DIR/system-$DST.db"
rm -f "$DB_DIR/system-$DST.db-shm"
rm -f "$DB_DIR/system-$DST.db-wal"
dev/ch2 no-op

echo "loading data into $DB_DIR/database-$VER.db"
sqlite3 "$DB_DIR/database-$VER.db" < "$TMP_DIR/dump-$VER.db"

# this has to come after loading data to avoid uniqueness conflicts
echo "adding default config"
dev/ch2 --dev config default --no-diary


# you almost certainly want to change the following details

echo "adding personal constants to $DB_DIR/database-$VER.db"
dev/ch2 --dev constants set FTHR.Bike 154
dev/ch2 --dev constants set FTHR.MTB 154
dev/ch2 --dev constants set FTHR.Road 154
dev/ch2 --dev constants set FTHR.Walk 154
dev/ch2 --dev constants set SRTM1.Dir /home/andrew/archive/srtm1
dev/ch2 --dev constants set Data.Dir /tmp/ch2
# the name of this constant depends on the kit name and so we must add it ourselves
dev/ch2 --dev constants add --single Power.cotic \
  --description 'Bike namedtuple values to calculate power for this kit' \
  --validate ch2.stats.calculate.power.Bike
dev/ch2 --dev constants set Power.cotic '{"cda": 0.42, "crr": 0.0055, "weight": 12}'


echo "next, run 'ch2 activities' or similar to load data"
