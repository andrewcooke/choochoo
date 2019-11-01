#!/bin/bash

dev/ch2 jupyter stop
sleep 3

VERSION=`grep 'CH2_VERSION =' ch2/commands/args.py | sed -e "s/.*CH2_VERSION = '\([0-9]\+\.[0-9]\+\).*/\1/"`
VERSION=`echo $VERSION | sed -e s/\\\\./-/g`
sqlite3 ~/.ch2/"database-$VERSION.sql" 'pragma journal_mode=delete'
