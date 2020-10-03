#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
DEV="-dev"
DEV2="--dev"
RESET=0
PGCONF=postgres-default.conf

help () {
    echo -e "\n  Run the postgres image (only)"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--reset] [--prof] [--no-dev] [-h]"
    echo -e "\n  --reset:     re-create the disks"
    echo -e "  --prof:      use the pgbadger conf for postgres (profiling)"
    echo -e "  --no-dev:    don't use dev-specific disks"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "--no-dev" ]; then
        DEV=
        DEV2=
    elif [ $1 == "--prof" ]; then
	PGCONF=postgres-pgbadger.conf
    elif [ $1 == "--reset" ]; then
        RESET=1
    elif [ $1 == "-h" ]; then
        help
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

./prune.sh

if (( RESET )); then
    ./make-postgresql-data-volume.sh $DEV2
    ./make-postgresql-log-volume.sh $DEV2
fi

rm -f postgres.conf
ln -s $PGCONF postgres.conf

docker run --rm -p 127.0.0.1:5432:5432 \
       -e POSTGRES_HOST_AUTH_METHOD=trust \
       -v "postgresql-data$DEV":/var/lib/postgresql/data \
       -v "postgresql-log$DEV":/var/log \
       -v `pwd`/postgres.conf:/etc/postgresql/postgresql.conf \
       --shm-size=1g \
       --name=postgresql \
       postgis/postgis:13-3.0-alpine \
       -c 'config_file=/etc/postgresql/postgresql.conf'

