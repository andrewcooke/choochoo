#!/bin/bash -x

# use 'official' version (not CH2_VERSION)
VERSION=`grep 'version=' setup.py | sed -e "s/.*version='\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/"`
echo "VERSION=$VERSION"

# enable ** globbing
shopt -s globstar

cd /tmp
rm -fr ch2
mkdir ch2
cd ch2
python3.7 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install choochoo==$VERSION || exit 1
ch2 --dev -f `pwd`/ch2.sql config default
ch2 --dev -f `pwd`/ch2.sql activities --fast ~/archive/fit/bike/**/*.fit
ch2 --dev -f `pwd`/ch2.sql monitor ~/archive/fit/monitor/*.fit
