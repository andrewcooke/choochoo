#!/bin/bash

rm -fr env
virtualenv env -p python3.7
source env/bin/activate
pip install --upgrade pip
pip install urwid
pip install sqlalchemy
pip install nose
pip install robotframework
pip install openpyxl

pip install setuptools wheel twine
#pip install more-itertools

echo "source env/bin/activate"
