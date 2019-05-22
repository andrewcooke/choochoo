#!/bin/bash -x

VERSION=`grep 'CH2_VERSION =' ch2/commands/args.py | sed -e "s/.*CH2_VERSION = '\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/"`

cd /tmp
rm -fr ch2
mkdir ch2
cd ch2
python3.7 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install choochoo==$VERSION || exit 1
ch2 --dev -f `pwd`/ch2.sql default-config
ch2 --dev -f `pwd`/ch2.sql activities --fast ~/archive/fit/bike/*.fit
ch2 --dev -f `pwd`/ch2.sql monitor ~/archive/fit/monitor/*.fit
