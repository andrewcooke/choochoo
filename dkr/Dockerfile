# syntax=docker/dockerfile:experimental
from python:3.8.3-slim-buster
workdir /tmp
run apt-get update
run apt-get -y install sqlite3 libsqlite3-dev libpq-dev npm gcc emacs
copy dkr/requirements.txt /tmp
run --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install wheel && \
    pip install -r requirements.txt
copy js/package.json js/package-lock.json js/webpack.config.js js/.babelrc      /app/js/
workdir /app/js
run npm install -g npm@next
run npm install
# do this after install so that we use a separate layer
copy js/src /app/js/src
run npm run build
workdir /app/py
copy py/ch2 /app/py/ch2
copy py/setup.py py/MANIFEST.in /app/py/
run pip install .
workdir /app
copy data/sdk/Profile.xlsx /app
run ch2 package-fit-profile ./Profile.xlsx
workdir /
expose 8000 8001
copy dkr/start-docker.sh .
cmd ./start-docker.sh
