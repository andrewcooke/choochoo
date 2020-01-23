#!/bin/bash

sqlite3 ~/.ch2/database.sqlc <<EOF
.output /tmp/dump-c.sql
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

rm ~/.ch2/database.sqld
dev/ch2 create-database

sqlite3 ~/.ch2/database.sqld < /tmp/dump-c.sql
dev/ch2 add-fthr 154 2000-01-01
dev/ch2 add-activity Cycling ~/archive/fit -f --month

