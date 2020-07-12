#!/bin/bash

dev/killall.sh
dev/shutdown.sh

VERSION=`grep 'CH2_VERSION =' py/ch2/commands/args.py | sed -e "s/.*CH2_VERSION *= *'\([0-9]\+\.[0-9]\+\)\.[0-9]\+'.*/\1/"`
VERSION=`echo $VERSION | sed -e s/\\\\./-/g`
echo -e "\nVERSION=$VERSION"

BASE=~/.ch2/$VERSION
echo -e "\nBASE=$BASE"

if [ ! -d $BASE ]; then
    echo -e "\nmissing $BASE"
    exit 1
fi

echo -e "\ndeleting $BASE"
rm -fr $BASE

echo -e "\ndeleting database"
psql -Upostgres -hlocalhost -c "drop database if exists \"activity-$VERSION\""

echo -e "\nreinstalling"
dev/ch2 --dev --color DARK database load acooke

echo -e "\nupgrading old data"
dev/ch2 --dev upgrade $TEMP

echo -e "\nrebuilding"
dev/ch2 --dev upload
