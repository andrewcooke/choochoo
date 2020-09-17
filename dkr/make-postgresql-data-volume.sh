#!/bin/bash

CMD=$0
DEV=

help () {
    echo -e "\n  Create a data volume for postgres data"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--dev] [-h]"
    echo -e "\n  --dev:       dev-specific"
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

if [ -z "$DEV" ]; then
    # delete this is you really want to
    echo "refusing to delete existing database"
    exit 2
fi

./prune.sh
docker volume rm -f "postgresql-data$DEV"
docker volume create "postgresql-data$DEV"
docker volume ls

