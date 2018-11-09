#!/bin/bash

source env/bin/activate

if [ "$#" -ne 1 ]; then
    echo "usage: $0 version"
    echo "eg: $0 1.2.3"
    OLD_VERSION=`grep version= ch2/command/args.py | sed -e "s/.*version='\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/"`
    echo "old version is $OLD_VERSION"
    exit 1
fi

VERSION=$1

OLD_VERSION=`grep version= ch2/command/args.py | sed -e "s/.*version='\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/"`
echo "command/args.py: $OLD_VERSION -> $VERSION"
sed -i ch2/command/args.py -e "s/\(.*version='\)\([0-9]\+\.[\0-9]\+\.[0-9]\+\)\('.*\)/\1$VERSION\3/"

OLD_VERSION=`grep version= setup.py | sed -e "s/.*version='\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/"`
echo "setup.py: $OLD_VERSION -> $VERSION"
sed -i setup.py -e "s/\(.*version='\)\([0-9]\+\.[\0-9]\+\.[0-9]\+\)\('.*\)/\1$VERSION\3/"

dev/document-cmds.sh

git commit -am "version $VERSION"
git push
git tag -a "v$VERSION" -m "version $VERSION"
git push origin "v$VERSION"

dev/package-profile.sh
dev/package-python.sh
#twine upload --repository-url https://test.pypi.org/legacy/ dist/*
twine upload dist/*

rm -fr build
