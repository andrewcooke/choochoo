#!/bin/bash

docker run --rm \
       -p 127.0.0.1:8000:8000 \
       -p 127.0.0.1:8001:8001 \
       -v disk-data:/data \
       --shm-size=1g \
       --name=ch2 \
       ch2
