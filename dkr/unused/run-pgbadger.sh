#!/bin/bash

CMD=$0
DEV=

help () {
    echo -e "\n  Run pdbadger on the postgres log"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--dev] [-h]"
    echo -e "\n  --dev:       use dev-specific disk"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "--dev" ]; then
        DEV="-dev"
    elif [ $1 == "-h" ]; then
        help
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

docker run --rm \
       -v "postgresql-log$DEV":/var/log \
       --name=pgbadger \
       uphold/pgbadger -o - -j 4 -x html /var/log/postgresql/postgresql.log > out.html

