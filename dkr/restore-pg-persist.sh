#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
DEV=
DIR=

help () {
    echo -e "\n  Restore the postgres data"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--reset] [--prof] [--dev] DIR [-h]"
    echo -e "\n  --dev:       use dev-specific disks"
    echo -e "   DIR:        the directory containing data.tgz"
    echo -e "   -h:         show this message\n"
    echo -e "\nBy default this restores the non-dev data to the dev disk."
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "--dev" ]; then
        DEV="-dev"
    elif [ $1 == "-h" ]; then
        help
    else
	if [ -z "$DIR" ]; then
	    DIR=$1
	else
            echo -e "\nERROR: do not understand $1\n"
            help
	fi
    fi
    shift
done

if [ -z "$DIR" ]; then
    echo -e "\nERROR: provide DIR"
    exit 2
fi

if [ ! -e "$DIR/data.tgz" ]; then
    echo -e "\nERROR: No data at $DIR/data.tgz"
    exit 2
fi

./prune.sh

docker run --rm \
       -v "postgresql-data$DEV":/var/lib/postgresql/data \
       -v "$DIR":/tmp/backup \
       --name=postgresql \
       --entrypoint "" \
       postgis/postgis:13-3.0-alpine \
       tar xvfz /tmp/backup/data.tgz -C /var/lib/postgresql

