#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit
./make-choochoo-image.sh --dev
./make-jupyter-image.sh --dev
