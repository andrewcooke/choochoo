#!/bin/bash

./prune.sh
docker volume rm -f pg-data
docker volume create pg-data
docker volume ls

