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
pip install tornado
pip install ipython
pip install notebook
pip install psutil
pip install textblob

pip install matplotlib

# these are reqs for mayavi (some are missing, others to avoid errors on install)
pip install ipywidgets
pip install ipyevents
pip install vtk
pip install mayavi

pip install setuptools wheel twine
pip install s-tui

echo "source env/bin/activate"
