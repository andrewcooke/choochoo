#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
SRC=
DEV=
DIR=/tmp/backup-pg-persist

help () {
    echo -e "\n  Restore the postgres data"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--reset] [--prof] [--dev] [--src-dev] [-h]"
    echo -e "\n  --dev:       use dev-specific disks"
    echo -e "   --src-dev:    use the dev-specific backup"
    echo -e "   -h:         show this message\n"
    echo -e "\nBy default this restores the non-dev data to the dev disk."
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "--dev" ]; then
        DEV="-dev"
    elif [ $1 == "--src-dev" ]; then
	SRC="-dev"
    elif [ $1 == "-h" ]; then
        help
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

./prune.sh

FULLDIR="${DIR}${SRC}"
if [ ! -e "$FULLDIR" ]; then
    echo -e "\nNo data at $FULLDIR"
    exit 2
fi

docker run --rm \
       -v "postgresql-data$DEV":/var/lib/postgresql/data \
       -v "$FULLDIR":/tmp/backup \
       --name=postgresql \
       --entrypoint "" \
       postgis/postgis:13-3.0-alpine \
       tar xvfz /tmp/backup/data.tgz -C /var/lib/postgresql

