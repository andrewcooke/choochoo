#!/bin/bash

dkr/run-pg-transient.sh &

function cleanup {
    docker stop $(docker ps -a -q)
}

trap cleanup EXIT
echo "waiting for database startup"
sleep 10
source py/env/bin/activate
ch2 db add user
ch2 db add database
PYTHONPATH=py python -m unittest py/tests/*.py |& tee tests.log
