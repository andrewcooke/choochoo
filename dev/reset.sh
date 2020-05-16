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

ACTIVITY=$BASE/data/activity.db
if [ ! -f $ACTIVITY ]; then
    echo -e "\nmissing $BASE/data/activity.db"
    exit 1
fi

TEMP=/tmp/activity-reset.db
rm -f $TEMP
echo -e "\ncopying $ACTIVITY to $TEMP"
cp $ACTIVITY $TEMP

echo -e "\ndeleting $BASE"
rm -fr $BASE

echo -e "\nreinstalling"
dev/ch2 --dev --color DARK configure load acooke

echo -e "\nupgrading old data"
dev/ch2 --dev upgrade $TEMP

echo -e "\nrebuilding"
dev/ch2 --dev upload
