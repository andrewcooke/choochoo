#!/bin/bash

# 'experimental' and DOCKER_BUILDKIT is related to the pip cache
# https://stackoverflow.com/a/57282479

VERSION=`grep 'CH2_VERSION =' ../py/ch2/commands/args.py | sed -e "s/.*CH2_VERSION *= *'\([0-9]\+\.[0-9]\+\)\.[0-9]\+'.*/\1/"`
VERSION=`echo $VERSION | sed -e s/\\\\./-/g`
CMD=$0
BASE=python:3.8.3-slim-buster
COMMENT="# use --cache with buildkit to enable pip cache"
MOUNT=
URI="--sqlite"
FILE="Dockerfile"
NET="choochoo"

help () {
    echo -e "\n  Create the dev image used to run Choochoo in Docker"
    echo -e "\n  Usage:"
    echo -e "\n    $CMD [--big] [--cache] [--pg] [--net NAME] [-h] [FILE]"
    echo -e "\n    FILE:      destination file name (default Dockerfile)"
    echo -e "  --big:       use larger base distro"
    echo -e "  --cache:     mount pip cache (buildkit)"
    echo -e "  --pg:        assume a postgres database on host pg"
    echo -e "  --net NAME:  netowrk name (container name)"
    echo -e "  --h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "-h" ]; then
	help
    elif [ $1 == "--big" ]; then
	BASE=python:3.8.3-slim-buster
    elif [ $1 == "--cache" ]; then
	COMMENT="# syntax=docker/dockerfile:experimental"
	MOUNT="--mount=type=cache,target=/root/.cache/pip"
    elif [ $1 == "--pg" ]; then
	URI="--uri postgresql://postgres@pg/activity-$VERSION"
    elif [ $1 == "--net" ]; then
	shift
	NET=$1
    else
	echo -e "\n  do not understand $1\n"
	help
    fi
    shift
done

pushd .. > /dev/null
source py/env/bin/activate

pip freeze > requirements.txt

cat > $FILE <<EOF
$COMMENT
from $BASE
workdir /tmp
run apt-get update
run apt-get -y install \\
    sqlite3 libsqlite3-dev \\
    libpq-dev gcc \\
    emacs
copy requirements.txt /tmp
run $MOUNT \\
    pip install --upgrade pip && \\
    pip install wheel && \\
    pip install -r requirements.txt
copy py /app
workdir /app    
run pip install .
expose 8000 8001
cmd ch2 --dev --base /data web service \\
    $URI \\
    --web-bind $NET --jupyter-bind $NET --proxy-bind 'localhost'
EOF

echo -e "\ncreated $FILE for $VERSION ($URI)\n"
