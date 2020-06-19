#!/bin/bash

# assuming that the containers are not already present (which prune fixes)
# then this starts a new, empty server and postgres.

./prune.sh
rm docker-compose.yml
ln -s docker-compose-test-postgresql.yml docker-compose.yml
docker-compose up
