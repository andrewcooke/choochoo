#!/bin/bash

CMD=$0
PGCONF=postgres-nolog.conf

help () {
    echo -e "\n  Run the postgres image (only)"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [-h]"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "-h" ]; then
        help
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

rm -f postgres.conf
ln -s $PGCONF postgres.conf

docker run --rm -p 127.0.0.1:5432:5432 \
       -e POSTGRES_HOST_AUTH_METHOD=trust \
       -v `pwd`/postgres.conf:/etc/postgresql/postgresql.conf \
       --shm-size=1g \
       --name=postgresql \
       postgis/postgis:13-3.0-alpine \
       -c 'config_file=/etc/postgresql/postgresql.conf'
