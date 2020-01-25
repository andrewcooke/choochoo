#!/bin/bash

dev/make-env.sh
pushd py
source env/bin/activate
pip install .
ch2 config check --no-data --no-config
