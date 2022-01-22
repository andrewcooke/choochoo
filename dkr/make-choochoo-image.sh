#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
BIG=
SLOW=
DEV=
DDEV=
BUILDKIT=1
PRUNE=0
FILE=`pwd`/Dockerfile.local

help () {
    echo -e "\n  Create the image used to run Choochoo in Docker"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--big] [--slow] [--dev] [--js] [--prune] [-h] [FILE]"
    echo -e "\n    FILE:      destination file name (default Dockerfile)"
    echo -e "  --big:       use larger base distro"
    echo -e "  --slow:      do not mount pip cache (buildkit)"
    echo -e "  --dev:       separate image used for development"
    echo -e "  --prune:     wipe old data"
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
	DEV="-dev"
	DDEV="--dev"
    elif [ $1 == "--prune" ]; then
        PRUNE=1
    else
	echo -e "\nERROR: do not understand $1\n"
	help
    fi
    shift
done

if (( PRUNE )); then ./prune.sh; fi

CMD="./make-choochoo-dockerfile.sh $DDEV $BIG $SLOW $FILE"
echo -e "\n> $CMD\n"
eval $CMD

echo
cat $FILE
echo

pushd .. > /dev/null
CMD="DOCKER_BUILDKIT=$BUILDKIT docker build --network host --tag andrewcooke/choochoo:latest-local$DEV -f $FILE ."
echo -e "\n> $CMD\n"
eval $CMD
popd > /dev/null

rm $FILE

echo -e "\nIMPORTANT: YOU SHOULD ALSO UPDATE THE JUPYTER IMAGE\n"
