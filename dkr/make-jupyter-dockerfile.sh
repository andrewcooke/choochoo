#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

# 'experimental' and DOCKER_BUILDKIT is related to the pip cache
# https://stackoverflow.com/a/57282479

VERSION=`grep 'CH2_VERSION =' ../py/ch2/commands/args.py | sed -e "s/.*CH2_VERSION *= *'\([0-9]\+\.[0-9]\+\)\.[0-9]\+'.*/\1/"`
VERSION=`echo $VERSION | sed -e s/\\\\./-/g`
CMD=$0

BASE=jupyter/scipy-notebook:latest
COMMENT="# syntax=docker/dockerfile:experimental"
MOUNT="--mount=type=cache,target=/root/.cache/pip"
FILE="Dockerfile.jupyter"

help () {
    echo -e "\n  Create the file used to extend Jupyter with Choochoo"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--big] [--slow] [--js] [-h] [FILE]"
    echo -e "\n    FILE:      destination file name (default Dockerfile)"
    echo -e "  --slow:      do not mount pip cache (buildkit)"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "-h" ]; then
	help
    elif [ $1 == "--slow" ]; then
	COMMENT="# pip cache disabled with --slow"
	MOUNT=
    else
	FILE=$1
    fi
    shift
done

source ../py/env/bin/activate

# basic image and support
# (we need to install db libs whatever db we are using because of python deps)
cat > $FILE <<EOF
$COMMENT
from $BASE
user root
workdir /tmp
run apt-get update
run apt-get -y install libpq-dev gcc emacs
EOF

# python install of ch2 package
cat >> $FILE <<EOF
workdir /app/py
copy py/ch2 /app/py/ch2
copy py/setup.py py/MANIFEST.in /app/py/
run pip install .
EOF

# revert directory where tree is mounted
cat >> $FILE <<EOF
workdir /home/jovyan/work
EOF

echo -e "\ncreated $FILE for $VERSION\n"
