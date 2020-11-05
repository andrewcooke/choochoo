#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
SLOW=
DEV=
BUILDKIT=1
PRUNE=0
FILE=`pwd`/Dockerfile.jupyter

help () {
    echo -e "\n  Create the image used to run Choochoo in Docker"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--slow] [--dev] [--prune] [-h] [FILE]"
    echo -e "\n    FILE:      destination file name (default Dockerfile)"
    echo -e "  --slow:      do not mount pip cache (buildkit)"
    echo -e "  --dev:       separate image used for development"
    echo -e "  --prune:     wipe old data"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "-h" ]; then
	help
    elif [ $1 == "--slow" ]; then
	SLOW=$1
	BUILDKIT=0
    elif [ $1 == "--dev" ]; then
        DEV="-dev"
    elif [ $1 == "--prune" ]; then
        PRUNE=1
    else
	echo -e "\nERROR: do not understand $1\n"
	help
    fi
    shift
done

if (( PRUNE )); then ./prune.sh; fi

CMD="./make-jupyter-dockerfile.sh $SLOW $FILE"
echo -e "\n> $CMD\n"
eval $CMD

echo
cat $FILE
echo

pushd .. > /dev/null
CMD="DOCKER_BUILDKIT=$BUILDKIT docker build --network host --tag andrewcooke/jupyter:latest-local$DEV -f $FILE ."
echo -e "\n> $CMD\n"
eval $CMD
popd > /dev/null
rm $FILE
