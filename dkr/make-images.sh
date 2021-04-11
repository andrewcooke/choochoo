#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
DEV='--dev'

help () {
    echo -e "\n  Create all (ch2 and Jupyter) images"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--no-dev]"
    echo -e "\n  --no-dev:    create normal (non-dev) images\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "-h" ]; then
	help
    elif [ $1 == "--no-dev" ]; then
	DEV=
    else
	echo -e "\nERROR: do not understand $1\n"
	help
    fi
    shift
done

./make-choochoo-image.sh $DEV
./make-jupyter-image.sh $DEV
