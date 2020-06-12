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

cat > dockerfile <<EOF
from python:3.8.3-slim-buster
#from python:3.8.3-buster
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
cmd ch2 --dev --base /data web service \
    --uri postgresql://postgres@pg/activity-0-34 \
    --bind ch2
EOF
docker build --network=host --tag ch2 -f dockerfile .

rm -fr app
rm dockerfile
