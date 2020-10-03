#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

HASH=`docker ps -aqf 'name=postgresql'`
VERSION=`grep 'CH2_VERSION =' ../py/ch2/commands/args.py | sed -e "s/.*CH2_VERSION *= *'\([0-9]\+\.[0-9]\+\)\.[0-9]\+'.*/\1/"`
VERSION=`echo $VERSION | sed -e s/\\\\./-/g`

docker exec -it $HASH psql -Udefault -hlocalhost activity-$VERSION
