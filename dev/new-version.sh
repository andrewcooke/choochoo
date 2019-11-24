#!/bin/bash

source env/bin/activate

if [ "$#" -ne 1 ]; then
    echo "usage: $0 version"
    echo "eg: $0 1.2.3"
    OLD_VERSION=`grep 'version=' setup.py | sed -e "s/.*version='\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/"`
    echo "old version is $OLD_VERSION"
    exit 1
fi

VERSION=$1

if [ `echo "$VERSION" | sed -e 's/[0-9]\+\.[\0-9]\+\.[0-9]\+//'` ]; then
    echo "error: bad version format"
    exit 2
fi

if [ `git rev-parse --abbrev-ref HEAD` != "master" ]; then
    echo "error: not on master"
    exit 3
fi

OLD_VERSION=`grep 'CH2_VERSION =' ch2/commands/args.py | sed -e "s/.*CH2_VERSION = '\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/"`
echo "commands/args.py: $OLD_VERSION -> $VERSION"
sed -i ch2/commands/args.py -e "s/\(.*CH2_VERSION = '\)\([0-9]\+\.[\0-9]\+\.[0-9]\+\)\('.*\)/\1$VERSION\3/"

OLD_VERSION=`grep 'version=' setup.py | sed -e "s/.*version='\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/"`
echo "setup.py: $OLD_VERSION -> $VERSION"
sed -i setup.py -e "s/\(.*version='\)\([0-9]\+\.[\0-9]\+\.[0-9]\+\)\('.*\)/\1$VERSION\3/"

dev/build-cmds.sh
dev/build-docs.sh

git commit -am "version $VERSION"
git push
git tag -a "v$VERSION" -m "version $VERSION"
git push origin "v$VERSION"

dev/package-profile.sh
dev/package-python.sh
#twine upload --repository-url https://test.pypi.org/legacy/ dist/*
twine upload dist/*

rm -fr build
rm -fr choochoo.egg-info
