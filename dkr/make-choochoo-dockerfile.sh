#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

# 'experimental' and DOCKER_BUILDKIT is related to the pip cache
# https://stackoverflow.com/a/57282479

VERSION=$(grep 'CH2_VERSION =' ../py/ch2/commands/args.py | sed -e "s/.*CH2_VERSION *= *'\([0-9]\+\.[0-9]\+\)\.[0-9]\+'.*/\1/")
VERSION=$(echo $VERSION | sed -e s/\\./-/g)
CMD=$0

BASE=python:3.9.1-slim-buster
COMMENT="# syntax=docker/dockerfile:experimental"
MOUNT="--mount=type=cache,mode=0777,target=/root/.cache/pip"
JS_PKG="npm"
FILE="Dockerfile"

help() {
  echo -e "\n  Create the file used to install Choochoo in Docker"
  echo -e "\n  Usage:"
  echo -e "\n   $CMD [--big] [--slow] [--js] [-h] [FILE]"
  echo -e "\n    FILE:      destination file name (default Dockerfile)"
  echo -e "  --big:       use larger base distro"
  echo -e "  --slow:      do not mount pip cache (buildkit)"
  echo -e "   -h:         show this message\n"
  exit 1
}

while [ $# -gt 0 ]; do
  if [ $1 == "-h" ]; then
    help
  elif [ $1 == "--big" ]; then
    BASE=python:3.9.1-buster
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
cat >$FILE <<EOF
$COMMENT
from $BASE
workdir /tmp
run apt-get update
run apt-get -y install sqlite3 libsqlite3-dev libpq-dev $JS_PKG gcc emacs
EOF

cat >>$FILE <<EOF
copy js/package.json js/package-lock.json js/config js/public /app/js/
copy js/config /app/js/config
copy js/public /app/js/public
workdir /app/js
run npm install -g npm@next
run npm install
# do this after install so that we use a separate layer
copy js/src /app/js/src
run npm run build
EOF

# https://pythonspeed.com/articles/docker-cache-pip-downloads/
cat >>$FILE <<EOF
workdir /app/py
copy py/ch2 /app/py/ch2
copy py/setup.py py/MANIFEST.in /app/py/
run rm -fr /app/py/ch2/web/static/*.js* /app/py/ch2/web/static/*.html /app/py/ch2/web/static/*.png /app/py/ch2/web/static/*.txt /app/py/ch2/web/static/*.ico
workdir /app/js
run cp -r build/* ../py/ch2/web/static
run cp src/workers/writer.js ../py/ch2/web/static
run touch ../py/ch2/web/static/__init__.py ../py/ch2/web/static/static/__init__.py ../py/ch2/web/static/static/js/__init__.py
workdir /app/py
run $MOUNT pip install .
EOF

cat >>$FILE <<EOF
workdir /app
copy data/sdk/Profile.xlsx /app
run ch2 package-fit-profile ./Profile.xlsx
EOF

# finally, start up
cat >>$FILE <<EOF
workdir /
expose 8000 8001
copy dkr/start-docker.sh .
cmd ./start-docker.sh
EOF

echo -e "\ncreated $FILE for $VERSION\n"
