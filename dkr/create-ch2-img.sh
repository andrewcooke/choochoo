#!/bin/bash

pushd ..
source py/env/bin/activate

rm -fr app
mkdir app

# give an argument to avoid js build
if [ $# -eq 0 ]; then
    dev/package-bundle.sh
fi

pushd py
rsync --exclude tests \
      --exclude __pycache__ \
      --exclude env \
      --exclude dist \
      --exclude *.pyc \
      --exclude *.iml \
      -r . ../app
popd

source py/env/bin/activate
pip freeze > requirements.txt

# 'experimental' and DOCKER_BUILDKIT below is related to the pip cache
# https://stackoverflow.com/a/57282479
cat > dockerfile <<EOF
# syntax=docker/dockerfile:experimental
#from python:3.8.3-slim-buster
from python:3.8.3-buster
workdir /tmp
run apt-get update
run apt-get -y install \
    sqlite3 libsqlite3-dev \
    libpq-dev gcc \
    emacs
copy requirements.txt /tmp
run --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install wheel && \
    pip install -r requirements.txt
copy app /app
workdir /app    
run pip install .
expose 8000
cmd ch2 --dev --base /data web service \
    --uri postgresql://postgres@pg/activity-0-34 \
    --web-bind ch2 --jupyter-bind ch2 --proxy-bind 'localhost'
EOF
DOCKER_BUILDKIT=1 docker build --network=host --tag ch2 -f dockerfile .

rm -fr app
rm requirements.txt
rm dockerfile
