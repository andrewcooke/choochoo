#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
PGCONF=postgres-nolog.conf
LOG=0

help () {
    echo -e "\n  Run the postgres image (only)"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--log] [-h]"
    echo -e "\n  --log:       enable logging"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "-h" ]; then
        help
    elif [ $1 == "--log" ]; then
        LOG=1
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

rm -f postgres.conf
ln -s $PGCONF postgres.conf

CMD="docker run --rm -p 127.0.0.1:5432:5432 \
       -e POSTGRES_HOST_AUTH_METHOD=trust \
       -v `pwd`/postgres.conf:/etc/postgresql/postgresql.conf \
       --shm-size=1g \
       --name=postgresql-transient \
       postgis/postgis:13-3.0-alpine \
       -c 'config_file=/etc/postgresql/postgresql.conf'"
if [ $LOG -eq 1 ]; then
    CMD="$CMD \
       -c 'log_statement=all'"
fi
echo $CMD
eval $CMD
