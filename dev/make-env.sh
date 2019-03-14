#!/bin/bash

rm -fr env
python3.7 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install cachetools
pip install urwid
pip install sqlalchemy
pip install openpyxl
pip install numpy
pip install pandas
pip install pyGeoTile
pip install colorama
pip install pendulum
pip install requests
pip install scipy
pip install bokeh
pip install tornado==5.1.1
pip install ipython
pip install notebook
pip install psutil

pip install textblob
pip install matplotlib
#pip install colorcet
#pip install webcolors

pip install setuptools wheel twine
pip install s-tui

echo "source env/bin/activate"
