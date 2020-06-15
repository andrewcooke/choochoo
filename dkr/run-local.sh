#!/bin/bash

rm docker-compose.yml
ln -s docker-compose-local.yml docker-compose.yml
if [ -f auto-prune ]; then docker container prune -f; fi
docker-compose up
