#!/bin/bash

sqlite3 ~/.ch2/database.sqla <<EOF
.output /tmp/dump-a.sql
.mode insert diary
select * from diary;
.mode insert injury
select * from injury;
.mode insert injury_diary
select * from injury_diary;
.mode insert schedule
select * from schedule;
.mode insert schedule_diary
select * from schedule_diary;
EOF

rm ~/.ch2/database.sqlb
dev/ch2 create-database

sqlite3 ~/.ch2/database.sqlb < /tmp/dump-a.sql
