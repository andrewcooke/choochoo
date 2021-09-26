#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

pushd .. >& /dev/null
source py/env/bin/activate
ch2 package-fit-profile data/sdk/Profile.xlsx

