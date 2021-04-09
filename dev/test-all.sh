#!/bin/bash

dkr/run-pg-transient.sh &
PID=$!

function cleanup {
    kill $PID
}

trap cleanup EXIT
echo "waiting for database startup"
sleep 5
source py/env/bin/activate
ch2 db add user
ch2 db add database
PYTHONPATH=py python -m unittest py/tests/*.py
