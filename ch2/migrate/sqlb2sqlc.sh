#!/bin/bash

sqlite3 ~/.ch2/database.sqlb <<EOF
.output /tmp/dump-b.sql
.mode insert diary
select * from diary;
.mode insert injury
select * from injury;
.mode insert injury_diary
select * from injury_diary;
.mode insert schedule_type
select * from schedule_type;
.mode insert schedule
select * from schedule;
.mode insert schedule_diary
select * from schedule_diary;
EOF

rm ~/.ch2/database.sqlc
dev/ch2 create-database

sqlite3 ~/.ch2/database.sqlc < /tmp/dump-b.sql
dev/ch2 add-fthr 154 2000-01-01
dev/ch2 add-activity Cycling ~/archive/fit -f --month

