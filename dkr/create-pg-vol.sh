#!/bin/bash

if [ -f auto-prune ]; then docker container prune -f; fi
docker volume rm -f pg-data
docker volume create pg-data
docker volume ls

