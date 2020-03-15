#!/bin/bash

sqlite3 ~/.ch2/database-0-30.sql<<EOF

update diary_topic 
   set schedule = 'd2018-03-11-2020-03-01', finish = 737485
 where name = 'Broken Femur LHS';

update diary_topic 
   set schedule = '2d[1]-2019-08-20', finish = 737291
 where name = 'Betaferon';

insert into diary_topic (name, sort, parent_id, schedule, start)
values ('Betaferon', 130, 3, '2019-08-27/2d[1]2019-08-27-', 737298);

EOF
