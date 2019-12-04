#!/usr/bin/env bash

rm -f /tmp/copy.sqlj
cp ~/.ch2/database.sqlj /tmp/copy.sqlj

sqlite3 /tmp/copy.sqlj <<EOF
pragma foreign_keys = on;
delete from source where type != 3;
EOF

cp /tmp/copy.sqlj /tmp/slim.sqlj
sqlite3 /tmp/slim.sqlj <<EOF
alter table statistic_journal add column time float default 0.0;
update statistic_journal set time = (select source.time from source where statistic_journal.source_id = source.id);
alter table source rename to old_source;
create table source (id integer not null, type integer not null);
insert into source select id, type from old_source;
update statistic_name set owner = 'Topic' where owner = 7403;
delete from statistic_name where owner != 'Topic';
update statistic_name set "constraint" = 'Topic "Diary" (d)' where "constraint" = 1;
update statistic_name set "constraint" = 'Topic "Multiple Sclerosis" (d)' where "constraint" = 3;
update statistic_name set "constraint" = 'Topic "Broken Femur LHS" (2018-03-11-)' where "constraint" = 4;
EOF

rm -f /tmp/dump-j.sql
sqlite3 /tmp/slim.sqlj <<EOF
.output /tmp/dump-j.sql
.mode insert activity_group
select * from activity_group;
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
.mode insert pipeline
select * from pipeline;
.mode insert topic_field
select * from topic_field;
.mode insert topic_journal
select * from topic_journal;
EOF

rm -f ~/.ch2/database.sqlk
dev/ch2 no-op

sqlite3 ~/.ch2/database.sqlk < /tmp/dump-j.sql

source env/bin/activate
PHYTHONPATH=. python <<EOF

from ch2.config import *
from ch2.squeal.tables.activity import ActivityGroup
from ch2.squeal.tables.statistic import StatisticJournal
from ch2.stoats.names import FTHR, BPM

log, db = config('')

with db.session_context() as s:
    c = Counter()
    bike = s.query(ActivityGroup).filter(ActivityGroup.name == 'Bike').one()
    run = s.query(ActivityGroup).filter(ActivityGroup.name == 'Run').one()
    add_activity_constant(s, bike, FTHR,
                          description='Heart rate at functional threshold (cycling). See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0',
                          units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)
    add_activity_constant(s, run, FTHR,
                          description='Heart rate at functional threshold (running).',
                          units=BPM, statistic_journal_type=StatisticJournalType.INTEGER)

EOF

dev/ch2 constants --set FTHR.Bike 154
