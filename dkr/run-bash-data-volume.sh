#!/bin/bash

DEV=

help () {
    echo -e "\n  Run bash with the data volume for choochoo data at /data"
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

docker run --rm -it \
       --name bash-data-volume \
       -v "choochoo-data$DEV":/data \
       -u $(id -u):$(id -g) \
       opensuse/leap \
       bash
