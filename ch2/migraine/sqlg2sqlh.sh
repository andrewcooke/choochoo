#!/bin/bash

rm -f /tmp/copy.sqlg
cp ~/.ch2/database.sqlg /tmp/copy.sqlg

rm -f /tmp/dump-g.sql
sqlite3 /tmp/copy.sqlg <<EOF
.output /tmp/dump-g.sql
pragma foreign_keys = on;
delete from source where type = 1;
delete from source where type = 2;
.mode insert activity
select * from activity;
.mode insert constant
select * from constant;
.mode insert constant_journal
select * from constant_journal;
.mode insert source
select * from source;
.mode insert statistic
select * from statistic;
.mode insert statistic_journal
select * from statistic_journal;
.mode insert statistic_journal_float
select * from statistic_journal_float;
.mode insert statistic_journal_integer
select * from statistic_journal_integer;
.mode insert statistic_journal_text
select * from statistic_journal_text;
.mode insert statistic_measure
select * from statistic_measure;
.mode insert topic
select * from topic;
.mode insert topic_field
select * from topic_field;
.mode insert topic_journal
select * from topic_journal;
.mode insert pipeline
select * from pipeline;
EOF

rm -f ~/.ch2/database.sqlh
dev/ch2 no-op

sqlite3 ~/.ch2/database.sqlh < /tmp/dump-g.sql
