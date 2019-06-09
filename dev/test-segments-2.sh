#!/bin/bash -e

mkdir -p test-segments-2

import() {
    if [ $# -ne 4 ]
    then
	echo "bad args"
	exit 1
    fi
    delta=$1
    match_bound=$2
    outer_bound=$3
    inner_bound=$4
    echo "$delta $match_bound $outer_bound $inner_bound"
    kargs="{\"delta\": $delta, \"match_bound\": $match_bound, \"outer_bound\": $outer_bound, \"inner_bound\": $inner_bound, \"sport_to_activity\": {\"cycling\": \"Bike\", \"running\": \"Run\"}}"
    echo "$kargs"
    cp ~/.ch2/database.sqlm-backup ~/.ch2/database.sqlm
    sqlite3 ~/.ch2/database.sqlm "update pipeline set kargs='$kargs' where id=1"
    dev/ch2 --dev activities ~/archive/fit/bike/2017-01-18* ~/archive/fit/bike/2017-02-09* ~/archive/fit/bike/2017-05-05* ~/archive/fit/bike/2017-07-12* ~/archive/fit/bike/2017-07-14* ~/archive/fit/bike/2017-08-08* ~/archive/fit/bike/2017-08-10* ~/archive/fit/bike/2017-08-12* ~/archive/fit/bike/2017-10-04* > test-segments-2/"l-$delta-$match_bound-$outer_bound-$inner_bound" 2>&1
    
    # dev/ch2 activities --fast ~/archive/fit/bike/2017*.fit > test-segments-2/"l-$delta-$match_bound-$outer_bound-$inner_bound" 2>&1
    
    dev/ch2 data segments > test-segments-2/"s-$delta-$match_bound-$outer_bound-$inner_bound"
    dev/ch2 data segment-journals > test-segments-2/"j-$delta-$match_bound-$outer_bound-$inner_bound"
    dev/ch2 data statistic-journals 'Segment Time' 'Segment Heart Rate' > test-segments-2/"x-$delta-$match_bound-$outer_bound-$inner_bound"
    cp ~/.ch2/database.sqlm test-segments-2/"db-$delta-$match_bound-$outer_bound-$inner_bound"
}


#import 0.01 25 50 5  # large match ok with large outer
#import 0.01 10 25 5  # compare stats w above (no difference)

for delta in 0.001 0.003 # 0.01 0.03 0.1 0.3 1
do
    import $delta 25 50 5
done

