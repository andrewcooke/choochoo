#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
DEV="-dev"
DEV2="--dev"
DIR=/tmp/backup-pg-persist

help () {
    echo -e "\n  Backup the postgres data"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--reset] [--prof] [--no-dev] [-h]"
    echo -e "\n  --no-dev:    don't use dev-specific disks"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "--no-dev" ]; then
        DEV=
        DEV2=
    elif [ $1 == "-h" ]; then
        help
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

./prune.sh

FULLDIR="${DIR}${DEV}"
if [ -e "$FULLDIR" ]; then
    rm -fr "$FULLDIR"
fi
mkdir "$FULLDIR"

docker run --rm \
       -v "postgresql-data$DEV":/var/lib/postgresql/data \
       -v "$FULLDIR":/tmp/backup \
       --name=postgresql \
       --entrypoint "" \
       postgis/postgis:13-3.0-alpine \
       tar cvfz /tmp/backup/data.tgz -C /var/lib/postgresql data

