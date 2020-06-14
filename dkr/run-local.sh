#!/bin/bash

rm docker-compose.yml
ln -s docker-compose-local.yml docker-compose.yml
docker container prune -f
docker-compose up

