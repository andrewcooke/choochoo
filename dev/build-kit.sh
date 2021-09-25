#!/bin/bash

dkr/run-pg-transient.sh &

function close {
    docker stop postgresql-transient
}
trap close exit

sleep 10
source py/env/bin/activate
gawk -f dev/build-doc.awk docs/kit.md-template > docs/kit.md
