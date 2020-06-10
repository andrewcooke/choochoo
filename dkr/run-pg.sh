#!/bin/bash

docker pull postgres:12.3-alpine
docker run --rm -p 127.0.0.1:5432:5432 \
       -e POSTGRES_HOST_AUTH_METHOD=trust \
       -v pg-data:/var/lib/postgresql/data \
       --shm-size=1g \
       --name=postgres \
       postgres:11.8-alpine
