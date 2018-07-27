#!/bin/bash

rm -fr env
virtualenv-3.5 env
source env/bin/activate
pip install --upgrade pip
pip install urwid
pip install sqlalchemy
pip install nose
pip install robotframework

pip install more-itertools
pip install openpyxl

echo "source env/bin/activate"
