#!/bin/bash

./prune.sh
docker volume rm -f postgresql-data
docker volume create postgresql-data
docker volume ls

