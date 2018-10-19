#!/bin/bash

sqlite3 ~/.ch2/database.sqle <<EOF
.output /tmp/dump-e.sql
delete from source where type = 1;
delete from source where type = 2;
.mode insert activity
select * from activity;
.mode insert activity_pipeline
select * from activity_pipeline;
.mode insert constant
select * from constant;
.mode insert constant_journal
select * from constant_journal;
.mode insert diary_pipeline
select * from diary_pipeline;
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
.mode insert statistic_pipeline
select * from statistic_pipeline;
.mode insert topic
select * from topic;
.mode insert topic_field
select * from topic_field;
.mode insert topic_journal
select * from topic_journal;
EOF

rm ~/.ch2/database.sqle
dev/ch2 no-op

sqlite3 ~/.ch2/database.sqle < /tmp/dump-e.sql
