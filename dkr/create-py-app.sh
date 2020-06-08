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
from opensuse/leap:15.1
copy app /app
workdir /app
run zypper --non-interactive install \
    	   python3 python3-devel python3-pip \
	   sqlite3 sqlite3-devel \
	   postgresql postgresql-devel \
           gcc
run pip install --upgrade pip && \
    pip install wheel && \
    pip install --no-cache-dir .
expose 8000
cmd ch2 web service
EOF
docker build --network=host --tag python -f dockerfile .

rm -fr app
rm dockerfile
