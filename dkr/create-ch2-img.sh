#!/bin/bash

pushd ..
source py/env/bin/activate

rm -fr app
mkdir app

dev/package-bundle.sh

pushd py
rsync --exclude tests \
      --exclude __pycache__ \
      --exclude env \
      --exclude dist \
      --exclude *.pyc \
      --exclude *.iml \
      -r . ../app
popd

cat > dockerfile <<EOF
from python:3.8.3-slim-buster
copy app /app
workdir /app
run apt-get update
run apt-get -y install \
    sqlite3 libsqlite3-dev \
    libpq-dev gcc
run pip install --upgrade pip && \
    pip install wheel && \
    pip install --no-cache-dir .
expose 8000
cmd ch2 --base /data web service
EOF
docker build --network=host --tag python -f dockerfile .

rm -fr app
rm dockerfile
