#!/bin/bash

if [ $# -ne 1 ]; then
    echo -e "\nusage:"
    echo -e "\n  $0 MIN"
    echo -e "\nwhere MIN is the number of minutes ago to include"
    exit 2
fi

MIN=$1

VERSION=`grep 'CH2_VERSION =' py/ch2/commands/args.py | sed -e "s/.*CH2_VERSION *= *'\([0-9]\+\.[0-9]\+\)\.[0-9]\+'.*/\1/"`
VERSION=`echo $VERSION | sed -e s/\\\\./-/g`
echo -e "\nVERSION=$VERSION"

BASE=~/.ch2/$VERSION
echo -e "\nBASE=$BASE"

TMP=/tmp/recent-errors
rm -f $TMP
touch $TMP

find $BASE/logs -mmin -$MIN -type f -print0 | while read -d $'\0' file; do
    echo -n "."
    name=`basename $file`
    for label in WARNING ERROR; do
	grep $label $file | while read -r line ; do
	    time=`echo $line | tr -s ' ' | cut -d ' ' -f 2-3 | sed s/:$//`
	    echo "$time $name $line" >> $TMP
	done
    done
done
echo

sort -r $TMP | cut -d ' ' -f 3-
