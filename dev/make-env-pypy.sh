#!/bin/bash

echo "this doesn't work"
exit 1

rm -fr env
/home/andrew/pkg/pypy3.5-6.0.0-linux_x86_64-portable/bin/virtualenv-pypy env
source env/bin/activate
pip install --upgrade pip
pip install urwid
pip install sqlalchemy
pip install openpyxl
pip install numpy
pip install pandas
pip install pyGeoTile
pip install colorama
pip install pendulum
pip install requests

pip install matplotlib
pip install bokeh
pip install colorcet
pip install webcolors
pip install jupyter

pip install setuptools wheel twine

echo "source env/bin/activate"
