#!/bin/bash -e

mkdir -p test-segments

for delta in 0.01 0.1 1
do
    for match_bound in 5 10 25
    do
	for outer_bound in 10 15 25
	do
	    for inner_bound in 2 5 7.5
	    do
		echo "$delta $match_bound $outer_bound $inner_bound"
		kargs="{\"delta\": $delta, \"match_bound\": $match_bound, \"outer_bound\": $outer_bound, \"inner_bound\": $inner_bound, \"sport_to_activity\": {\"cycling\": \"Bike\", \"running\": \"Run\"}}"
		echo "$kargs"
		cp ~/.ch2/database.sqlm-backup ~/.ch2/database.sqlm
		sqlite3 ~/.ch2/database.sqlm "update pipeline set kargs='$kargs' where id=1"
		dev/ch2 activities --fast ~/archive/fit/bike/2017*.fit > test-segments/"l-$delta-$match_bound-$outer_bound-$inner_bound" 2>&1
		dev/ch2 data segments > test-segments/"s-$delta-$match_bound-$outer_bound-$inner_bound"
		dev/ch2 data segment-journals > test-segments/"j-$delta-$match_bound-$outer_bound-$inner_bound"
	    done
	done
    done
done
