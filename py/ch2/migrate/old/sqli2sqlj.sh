#!/bin/bash

rm -f /tmp/copy.sqli
cp ~/.ch2/database.sqli /tmp/copy.sqli

rm -f /tmp/dump-i.sql
sqlite3 /tmp/copy.sqli <<EOF
alter table topic_field add column schedule text default '';
.output /tmp/dump-i.sql
--.mode insert 
--select * from ;
.mode insert activity_group
select * from activity_group;
.mode insert activity_journal
select * from activity_journal;
.mode insert activity_timespan
select * from activity_timespan;
.mode insert activity_waypoint
select * from activity_waypoint;
.mode insert constant
select * from constant;
.mode insert constant_journal
select * from constant_journal;
.mode insert file_scan
select * from file_scan;
.mode insert interval
select * from interval;
.mode insert monitor_heart_rate
select * from monitor_heart_rate;
.mode insert monitor_journal
select * from monitor_journal;
.mode insert monitor_steps
select * from monitor_steps;
.mode insert pipeline
select * from pipeline;
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
.mode insert statistic_measure
select * from statistic_measure;
.mode insert statistic_name
select * from statistic_name;
.mode insert system_constant
select * from system_constant;
.mode insert topic
select * from topic;
.mode insert topic_field
select * from topic_field;
.mode insert topic_journal
select * from topic_journal;
EOF

rm -f ~/.ch2/database.sqlj
dev/ch2 no-op

sqlite3 ~/.ch2/database.sqlj < /tmp/dump-i.sql
