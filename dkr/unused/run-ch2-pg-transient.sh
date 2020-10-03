#!/bin/bash

CMD=$0
BIG=
JS=
SLOW=
PGCONF=postgres-default.conf

help () {
    echo -e "\n  Run choochoo + postgres in transient containers"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--big] [--slow] [--js] [-h]"
    echo -e "\n  --big:       use larger base distro"
    echo -e "  --slow:      do not mount pip cache (buildkit)"
    echo -e "  --js:        assumes node pre-built"
    echo -e "  --prof:      use the pgbadger conf for postgres (profiling)"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "--big" ]; then
        BIG=$1
    elif [ $1 == "--slow" ]; then
        SLOW=$1
    elif [ $1 == "--js" ]; then
        JS=$1
    elif [ $1 == "--reset" ]; then
        RESET=1
    elif [ $1 == "--prof" ]; then
	PGCONF=postgres-pgbadger.conf
    elif [ $1 == "-h" ]; then
        help
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

./prune.sh

rm -f postgres.conf
ln -s $PGCONF postgres.conf

./make-choochoo-image.sh $BIG $SLOW $JS

rm docker-compose.yml
ln -s docker-compose-postgresql-transient.yml docker-compose.yml
docker-compose up
