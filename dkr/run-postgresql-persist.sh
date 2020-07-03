#!/bin/bash

docker run --rm -p 127.0.0.1:5432:5432 \
       -e POSTGRES_HOST_AUTH_METHOD=trust \
       -v postgresql-data:/var/lib/postgresql/data \
       -v postgresql-log:/var/logs \
       --shm-size=1g \
       --name=postgresql \
       postgres:11.8-alpine
