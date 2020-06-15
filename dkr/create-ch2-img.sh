#!/bin/bash

CMD=$0
FAST=0
BIG=
CACHE=

help () {
    echo -e "\n  Create the dev image used to run Choochoo in Docker"
    echo -e "\n  Usage:"
    echo -e "\n    $CMD [--fast] [--big] [--cache] [-h]"
    echo -e "\n  --fast:  don't build JS library"
    echo -e "  --big:   use larger base distro"
    echo -e "  --cache: mount pip cache (buildkit)"
    echo -e "  --h:     show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "-h" ]; then
	help
    elif [ $1 == "--fast" ]; then
	FAST=1
    elif [ $1 == "--big" ]; then
	BIG=$1
    elif [ $1 == "--cache" ]; then
	CACHE=$1
    else
	echo -e "\n  do not understand $1\n"
	help
    fi
    shift
done

./create-dockerfile.sh $BIG $CACHE

if [ $FAST -eq 0 ]; then
    dev/package-bundle.sh
else
    echo -e "\nWARNING: skipping JS build\n"
fi

pushd .. > /dev/null
DOCKER_BUILDKIT=1 docker build --network=host --tag ch2 .
