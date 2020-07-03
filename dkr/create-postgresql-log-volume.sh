#!/bin/bash

./prune.sh
docker volume rm -f postgresql-log
docker volume create postgresql-log
docker volume ls
docker run --rm -i -v postgresql-log:/var/log postgres:11.8-alpine /bin/bash <<EOF
mkdir /var/log/postgresql
chown postgres /var/log/postgresql
EOF
