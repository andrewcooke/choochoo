#!/bin/bash

docker pull postgres:12.3-alpine
docker run --rm -p 5432:5432 \
       -e POSTGRES_HOST_AUTH_METHOD=trust \
       -v pg-volume:/var/lib/postgresql/data \
       postgres:12.3-alpine

