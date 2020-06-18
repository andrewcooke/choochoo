#!/bin/bash

./prune.sh
docker run --rm \
       -p 127.0.0.1:8000:8000 \
       -p 127.0.0.1:8001:8001 \
       --name=choochoo \
       andrewcooke/choochoo:latest-local
