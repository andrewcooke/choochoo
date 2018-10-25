#!/bin/bash

# python 2 - only for experimenting with other packages

rm -fr env2
virtualenv env2 -p python2
source env2/bin/activate
pip install --upgrade pip
pip install python-dateutil
pip install requests
pip install sqlalchemy
#pip install Fit
pip install setuptools

echo "source env2/bin/activate"
