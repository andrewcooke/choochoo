#!/bin/bash

./prune.sh
docker pull andrewcooke/choochoo:latest-dev
docker run --rm \
       -p 127.0.0.1:8000:8000 \
       -p 127.0.0.1:8001:8001 \
       --shm-size 1g \
       andrewcooke/choochoo:latest-dev
