#!/bin/bash

rm -f /tmp/copy.sqle
rm -f ~/.ch2/database.sqlf
rm -f /tmp/dump-e.sql

cp ~/.ch2/database.sqle /tmp/copy.sqle

# delete all intervals
sqlite3 /tmp/copy.sqle "pragma foreign_keys = on; delete from source where type = 1;"
sqlite3 /tmp/copy.sqle "update statistic set owner=11132 where owner='ch2.stoats.calculate.activity.ActivityStatistics'"
sqlite3 /tmp/copy.sqle "update statistic set owner=9799 where owner='ch2.stoats.calculate.summary.SummaryStatistics'"
sqlite3 /tmp/copy.sqle "update statistic set owner=31048 where owner='ch2.squeal.tables.constant.Constant'"
sqlite3 /tmp/copy.sqle "update statistic set owner=7403 where owner='ch2.squeal.tables.topic.Topic'"
sqlite3 /tmp/copy.sqle "update statistic set owner=26704 where owner='ch2.stoats.calculate.monitor.MonitorStatistics'"

sqlite3 /tmp/copy.sqle <<EOF
.output /tmp/dump-e.sql
delete from source where type = 1;
delete from source where type = 2;
.mode insert activity
select * from activity;
.mode insert constant
select * from constant;
.mode insert constant_journal
select * from constant_journal;
.mode insert interval
select * from interval;
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

dev/ch2 no-op

sqlite3 ~/.ch2/database.sqlf < /tmp/dump-e.sql
