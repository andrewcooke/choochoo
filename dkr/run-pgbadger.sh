#!/bin/bash

docker run --rm \
       -v postgresql-log:/var/log \
       --name=pgbadger \
       uphold/pgbadger -o - -j 4 -x html /var/log/postgresql/postgresql.log > out.html

