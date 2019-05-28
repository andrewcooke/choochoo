#!/bin/bash

dev/make-env.sh
source env/bin/activate
pip install .
ch2 config check --no-data --no-config
