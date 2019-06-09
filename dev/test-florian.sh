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
ch2 --dev -v5 -f `pwd`/ch2.sql activities /home/andrew/project/ch2/choochoo/data/test/source/private/florian.fit /home/andrew/project/ch2/choochoo/data/test/source/other/920* -Kn_cpu=1
ch2 --dev -v5 -f `pwd`/ch2.sql jupyter show calendar
ch2 --dev -v5 -f `pwd`/ch2.sql jupyter show activity_details 2019-05-16 Bike

