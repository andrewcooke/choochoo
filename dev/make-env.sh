#!/bin/bash

rm -fr env
python3.7 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install urwid
pip install sqlalchemy
pip install nose
pip install robotframework
pip install openpyxl
pip install numpy
opip install pandas
pip install pyGeoTile
pip install colorama
pip install pendulum
pip install requests

pip install matplotlib
pip install bokeh
pip install jupyter

pip install setuptools wheel twine

echo "source env/bin/activate"
