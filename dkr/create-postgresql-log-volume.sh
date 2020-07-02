#!/bin/bash

./prune.sh
docker volume rm -f postgresql-log
docker volume create postgresql-log
docker volume ls
