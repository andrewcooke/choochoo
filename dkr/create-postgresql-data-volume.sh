#!/bin/bash

./prune.sh
docker volume rm -f postgresql-data
docker volume create ppostgresql-data
docker volume ls

