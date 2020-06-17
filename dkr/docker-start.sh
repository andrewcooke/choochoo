#!/bin/bash

# a startup script that runs inside the docker build
# this allows users to modify the bechabiour via environment variables
# currently only a sing value is supported:
# define CH2_DKR_POSTGRESQL to use the postgresql database
# this will tell the web server to connect to postgres - you must still
# configure and start the database (eg using docker compose).

if [ -z ${CH2_DKR_POSTGRESQL+x} ]; then
    DB="--sqlite"
else
    DB="--postgreql"
fi

CMD="ch2 --dev --base /data web service $DB --web-bind 0.0.0.0 --jupyter-bind 0.0.0.0 --proxy-bind 'localhost' --warn-data --warn-secure"
echo -e "\nrunning $CMD\n"

eval $CMD
