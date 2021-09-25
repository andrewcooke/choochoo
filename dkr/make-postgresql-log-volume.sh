#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
DEV=

help () {
    echo -e "\n  Create a data volume for postgres logs"
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

./prune.sh
docker volume rm -f "postgresql-log$DEV"
docker volume create "postgresql-log$DEV"
docker volume ls
docker run --rm -i -v "postgresql-log$DEV":/var/log postgis/postgis:13-3.0-alpine /bin/bash <<EOF
mkdir /var/log/postgresql
chown postgres /var/log/postgresql
EOF
