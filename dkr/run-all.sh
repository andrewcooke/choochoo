#!/bin/bash

docker run --rm -p 127.0.0.1:8000:8000 \
       -e POSTGRES_HOST_AUTH_METHOD=trust \
       -v pg-data:/var/lib/postgresql/data \
       -v disk-data:/data \
       --shm-size=1g \
       --name=ch2 \
       python
