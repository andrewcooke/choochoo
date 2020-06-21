#!/bin/bash

CMD=$0
DEV=
BIG=
SLOW=
RESET=0

help () {
    echo -e "\n  Run Choochoo + postgres with named volumes"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--big] [--slow] [--dev] [--reset] [-h] [FILE]"
    echo -e "\n    FILE:      destination file name (default Dockerfile)"
    echo -e "  --big:       use larger base distro"
    echo -e "  --slow:      do not mount pip cache (buildkit)"
    echo -e "  --dev:       dev work (assumes node pre-built)"
    echo -e "  --reset:     re-create the disks"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "-h" ]; then
        help
    elif [ $1 == "--big" ]; then
        BIG=$1
    elif [ $1 == "--slow" ]; then
        SLOW=$1
    elif [ $1 == "--dev" ]; then
        DEV=$1
    elif [ $1 == "--reset" ]; then
        RESET=1
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

./prune.sh

if (( RESET )); then
    ./create-postgresql-data-volume.sh
    ./create-choochoo-data-volume.sh
    ./create-choochoo-image.sh $DEV $BIG $SLOW
fi

rm docker-compose.yml
ln -s docker-compose-test-postgresql-persist.yml docker-compose.yml
docker-compose up
