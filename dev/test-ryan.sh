#!/bin/bash -x

cd /tmp
rm -fr ch2
mkdir ch2
cd ch2
git clone /home/andrew/project/ch2/choochoo
cd choochoo
git checkout dev
dev/install-in-env.sh
source env/bin/activate
ch2 --dev -v5 package-fit-profile /home/andrew/project/ch2/choochoo/data/sdk/Profile.xlsx
ch2 --dev -v5 -f `pwd`/ch2.sql config default
ch2 --dev -v5 -f `pwd`/ch2.sql monitor /home/andrew/project/ch2/choochoo/data/test/source/other/37140810636.fit -Kn_cpu=1

