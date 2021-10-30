#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0

help() {
    echo -e "\n  Install Python environment needed for AWS\n"
    echo -e "  Usage:"
    echo -e "    $CMD [-h]\n"
    echo -e "  -h:       show this text\n"
    exit 1
}

while [[ $# -gt 0 ]]; do

    case $1 in
	-h)
	    help
	    ;;
	*)
	    echo -e "\nERROR: did not understand $1"
	    exit 2
	    ;;
    esac
    shift
    
done


PYTHON=python3.9

pushd .. >& /dev/null
rm -fr env
$PYTHON -m venv env
source env/bin/activate

pip install --upgrade pip setuptools wheel twine
pip install apache-libcloud
