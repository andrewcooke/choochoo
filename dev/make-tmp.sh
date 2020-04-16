#!/bin/bash -x

dev/killall.sh
pushd /tmp
rm -fr ch2
mkdir ch2
cd ch2
BASE=`pwd`
popd
dev/ch2 --dev --base $BASE web start
