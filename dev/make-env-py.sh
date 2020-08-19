#!/bin/bash

PYTHON=python3.8

pushd py
rm -fr env
$PYTHON -m venv env
source env/bin/activate

pip install --upgrade pip setuptools wheel twine
source env/bin/activate
python setup.py develop
