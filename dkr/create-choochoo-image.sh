#!/bin/bash

CMD=$0
DEV=
BIG=
SLOW=
BUILDKIT=1
FILE=`pwd`/Dockerfile.local

help () {
    echo -e "\n  Create the dev image used to run Choochoo in Docker"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--big] [--slow] [--dev] [-h] [FILE]"
    echo -e "\n    FILE:      destination file name (default Dockerfile)"
    echo -e "  --big:       use larger base distro"
    echo -e "  --slow:      do not mount pip cache (buildkit)"
    echo -e "  --dev:       dev work (assumes node pre-built)"
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
	BUILDKIT=0
    elif [ $1 == "--dev" ]; then
	DEV=$1
    else
	echo -e "\nERROR: do not understand $1\n"
	help
    fi
    shift
done

./prune.sh

CMD="./create-dockerfile.sh $BIG $SLOW $DEV $FILE"
echo -e "\n> $CMD\n"
eval $CMD

echo
cat $FILE
echo

if [ "$DEV" == "" ]; then
    pushd .. > /dev/null
    dev/package-bundle.sh
    popd > /dev/null
else
    echo -e "\nWARNING: skipping JS build\n"
fi

pushd .. > /dev/null
CMD="DOCKER_BUILDKIT=$BUILDKIT docker build --network host --tag andrewcooke/choochoo:latest-local -f $FILE ."
echo -e "\n> $CMD\n"
eval $CMD
popd > /dev/null
rm $FILE
