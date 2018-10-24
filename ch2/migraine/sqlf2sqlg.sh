#!/bin/bash

rm -f /tmp/copy.sqlf
cp ~/.ch2/database.sqlf /tmp/copy.sqlf

rm -f /tmp/dump-f.sql
sqlite3 /tmp/copy.sqlf <<EOF
alter table topic_journal add column date integer default 0;
.output /tmp/dump-f.sql
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

rm -f ~/.ch2/database.sqlg
dev/ch2 no-op

sqlite3 ~/.ch2/database.sqlg < /tmp/dump-f.sql

source env/bin/activate
PHYTHONPATH=. python <<EOF

import datetime as dt
from ch2.command.args import bootstrap_file, m, V
from ch2.squeal.tables.topic import TopicJournal

class File:
    name = '/home/andrew/.ch2/database.sqlg'

args, log, db = bootstrap_file(File(), m(V), '5')

with db.session_context() as s:
    for t in s.query(TopicJournal).all():
        t.date = dt.date(*t.time.timetuple()[:3])

EOF
