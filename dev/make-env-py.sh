#!/bin/bash

PYTHON=python3.9
#PYTHON=python3.8

pushd py >& /dev/null
rm -fr env
$PYTHON -m venv env
source env/bin/activate

pip install --upgrade pip setuptools wheel twine
source env/bin/activate
#python setup.py develop
pip install -e .

