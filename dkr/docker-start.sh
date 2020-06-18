#!/bin/bash

# a startup script that runs inside the docker build this allows users
# to modify the behaviour via environment variables.

#currently only a single value is supported:

# define CH2_DKR_DB_URI to set the database URI.  this will tell the
# web server where to connect - you must still configure and start the
# database server, if required (eg using docker compose).

if [ -z ${CH2_DKR_URI+x} ]; then
    echo "CH2_DKR_URI undefined - will use sqlite"
    URI="--sqlite"  # does not need a separate server
else
    echo "CH2_DKR_URI=$CH2_DKR_URI"
    URI="--uri $CH2_DKR_URI"
fi

CMD="ch2 --dev --base /data web service $URI --web-bind 0.0.0.0 --jupyter-bind 0.0.0.0 --proxy-bind 'localhost' --warn-data --warn-secure"
echo -e "\nrunning $CMD\n"

eval $CMD
