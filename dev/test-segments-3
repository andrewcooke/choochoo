#!/bin/bash -e

mkdir -p test-segments-3

import() {
    if [ $# -ne 2 ]
    then
	echo "bad args"
	exit 1
    fi
    match_bound=$1
    inner_bound=$2
    echo "$match_bound $inner_bound"
    kargs="{\"match_bound\": $match_bound, \"inner_bound\": $inner_bound, \"sport_to_activity\": {\"cycling\": \"Bike\", \"running\": \"Run\"}}"
    echo "$kargs"
    cp ~/.ch2/database.sqlm-backup ~/.ch2/database.sqlm
    sqlite3 ~/.ch2/database.sqlm "update pipeline set kargs='$kargs' where id=1"
    dev/ch2 --dev activities ~/archive/fit/bike/2017-01-18* ~/archive/fit/bike/2017-02-09* ~/archive/fit/bike/2017-05-05* ~/archive/fit/bike/2017-07-12* ~/archive/fit/bike/2017-07-14* ~/archive/fit/bike/2017-08-08* ~/archive/fit/bike/2017-08-10* ~/archive/fit/bike/2017-08-12* ~/archive/fit/bike/2017-10-04* > test-segments-3/"l-$match_bound-$inner_bound" 2>&1
    
    dev/ch2 data segments > test-segments-3/"s-$match_bound-$inner_bound"
    dev/ch2 data segment-journals > test-segments-3/"j-$match_bound-$inner_bound"
    dev/ch2 data statistic-journals 'Segment Time' 'Segment Heart Rate' > test-segments-3/"x-$match_bound-$inner_bound"
    cp ~/.ch2/database.sqlm test-segments-3/"db-$match_bound-$inner_bound"
}

import 25 5

