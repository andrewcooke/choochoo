#!/bin/bash

DB=~/.ch2/database.sqlp

sqlite3 $DB <<EOF 
PRAGMA foreign_keys = ON;
select distinct name from statistic_name as n, statistic_journal as j, statistic_journal_text as t where n.id == j.statistic_name_id and j.id = t.id and t.value is null;
select distinct name from statistic_name as n, statistic_journal as j, statistic_journal_float as t where n.id == j.statistic_name_id and j.id = t.id and t.value is null;
select distinct name from statistic_name as n, statistic_journal as j, statistic_journal_integer as t where n.id == j.statistic_name_id and j.id = t.id and t.value is null;
EOF

sqlite3 $DB <<EOF 
PRAGMA foreign_keys = ON;
delete from statistic_journal where id in (select id from statistic_journal_text where value is null);
delete from statistic_journal where id in (select id from statistic_journal_float where value is null);
delete from statistic_journal where id in (select id from statistic_journal_integer where value is null);
EOF

