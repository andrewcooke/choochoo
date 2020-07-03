#!/bin/bash

CMD=$0
PRUNE=1

help () {
    echo -e "\n  Start the latest-local image"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--keep] [-h]"
    echo -e "\n  --keep:      don't wipe the old data"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "-h" ]; then
        help
    elif [ $1 == "--keep" ]; then
        PRUNE=0
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

if (( PRUNE )); then
    ./prune.sh;
fi

docker run \
       -p 127.0.0.1:8000:8000 \
       -p 127.0.0.1:8001:8001 \
       --name=choochoo \
       andrewcooke/choochoo:latest-local
