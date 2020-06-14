#!/bin/bash

docker container prune -f
docker volume rm -f pg-data
docker volume create pg-data
docker volume ls

