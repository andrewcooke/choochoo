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
dev/ch2 -v4 db remove database

echo -e "\nre-creating database"
# have to add user before database, because user owns database
dev/ch2 -v4 db add user
dev/ch2 -v4 db add database
dev/ch2 --dev db add profile acooke

echo -e "\nimporting old data"
dev/ch2 --dev import

exit 2

echo -e "\nrebuilding"
dev/ch2 --dev read

