#!/bin/bash

rm -fr dist
source env/bin/activate
python3 setup.py sdist bdist_wheel
