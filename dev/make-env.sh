#!/bin/bash

rm -fr env
python3.7 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install bokeh
pip install cachetools
pip install colorama
pip install jupyter
pip install matplotlib
pip install numpy
pip install openpyxl
pip install pandas
pip install pendulum
pip install psutil
pip install pyGeoTile
pip install pyproj
pip install rasterio
pip install requests
pip install scipy
pip install sentinelsat
pip install shapely
pip install sklearn
pip install sqlalchemy
pip install textblob
pip install urwid

pip install setuptools wheel twine
pip install s-tui

echo "source env/bin/activate"
