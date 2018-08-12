#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "usage: $0 version"
    echo "eg: $0 1.2.3"
    exit 1
fi

VERSION=$1

OLD_VERSION=`grep version= choochoo/args.py | sed -e "s/.*version='\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/"`
echo "args.py: $OLD_VERSION -> $VERSION"
sed -i choochoo/args.py -e "s/\(.*version='\)\([0-9]\+\.[\0-9]\+\.[0-9]\+\)\('.*\)/\1$VERSION\3/"

OLD_VERSION=`grep version= setup.py | sed -e "s/.*version='\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/"`
echo "setup.py: $OLD_VERSION -> $VERSION"
sed -i setup.py -e "s/\(.*version='\)\([0-9]\+\.[\0-9]\+\.[0-9]\+\)\('.*\)/\1$VERSION\3/"

git tag -a "v$VERSION" -m "version $VERSION"
git push origin "v$VERSION"

source env/bin/activate
python3 setup.py sdist bdist_wheel
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
