#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

# 'experimental' and DOCKER_BUILDKIT is related to the pip cache
# https://stackoverflow.com/a/57282479

VERSION=`grep 'CH2_VERSION =' ../py/ch2/commands/args.py | sed -e "s/.*CH2_VERSION *= *'\([0-9]\+\.[0-9]\+\)\.[0-9]\+'.*/\1/"`
VERSION=`echo $VERSION | sed -e s/\\\\./-/g`
CMD=$0

BASE=jupyterhub/jupyterhub
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
run apt-get -y install libpq-dev gcc emacs python3-dev
EOF

# create admin user
cat >> $FILE <<EOF
RUN useradd -m -p "$(openssl passwd -1 password)" choo_choo_admin
EOF

# python libs that are needed in all cases
cat >> $FILE <<EOF
copy dkr/requirements.txt /tmp
run $MOUNT \\
    pip install --upgrade pip && \\
    pip install wheel jupyter && \\
    pip install -r requirements.txt
EOF

# python install of ch2 package
cat >> $FILE <<EOF
workdir /app/py
copy py/ch2 /app/py/ch2
copy py/setup.py py/MANIFEST.in /app/py/
run pip install .
EOF

echo -e "\ncreated $FILE for $VERSION\n"
