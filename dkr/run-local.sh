#!/bin/bash

rm docker-compose.yml
ln -s docker-compose-local.yml docker-compose.yml
./prune.sh
docker-compose up
