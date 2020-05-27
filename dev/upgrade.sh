#!/bin/bash

dev/killall.sh
dev/shutdown.sh > /dev/null

BASE=~/.ch2

NEW_VERSION=`grep 'CH2_VERSION =' py/ch2/commands/args.py | sed -e "s/.*CH2_VERSION *= *'\([0-9]\+\.[0-9]\+\)\.[0-9]\+'.*/\1/"`
NEW_VERSION=`echo $NEW_VERSION | sed -e s/\\\\./-/g`
echo -e "\nNEW_VERSION=$NEW_VERSION"

pushd $BASE > /dev/null
OLD_VERSION=`ls -dv [0-9]*-[0-9]* | sort -n | grep -v $NEW_VERSION | tail -1`
if [ -z "$OLD_VERSION" ]; then
    echo -e "\ncould not find pervious version"
    exit 1
fi
popd > /dev/null
echo -e "\nOLD_VERSION=$OLD_VERSION"

NEW_BASE=$BASE/$NEW_VERSION
echo -e "\nNEW_BASE=$NEW_BASE"
OLD_BASE=$BASE/$OLD_VERSION
echo -e "\nOLD_BASE=$OLD_BASE"

sleep 10

ACTIVITY=$NEW_BASE/data/activity.db
if [ -f $ACTIVITY ]; then
    BACKUP=/tmp/activity-upgrade.db
    rm -f $BACKUP
    echo -e "\ncopying $ACTIVITY to $BACKUP"
    cp $ACTIVITY $BACKUP
fi

if [ -d $NEW_BASE ]; then
    echo -e "\ndeleting $NEW_BASE"
    rm -fr $NEW_BASE
fi

echo -e "\ninstalling"
dev/ch2 --dev --color DARK configure load acooke || { echo -e "\ninstall failed"; exit 2; }

echo -e "\nupgrading old data"
dev/ch2 --dev upgrade $OLD_VERSION || { echo -e "\nupgrade failed"; exit 3; }

if [ -e dev/set-constants.sh ]; then
    dev/set-constants.sh
fi

echo -e "\nrebuilding"
dev/ch2 --dev upload || { echo -e "\nupload failed"; exit 4; }

echo -e "\nchecking (and fixing)"
dev/ch2 check --fix
