#!/bin/bash -ex

shopt -s globstar
start=$SECONDS

./ch2/migraine/sqlq2sqlq.sh
cp ~/.ch2/database.sqlq ~/.ch2/database.sqlq-empty

#cp ~/.ch2/database.sqlq-empty ~/.ch2/database.sqlq

dev/ch2 --dev -v5 activities ~/archive/fit/bike/*.fit --fast -D 'Bike=Cotic Soul'
dev/ch2 --dev -v5 activities ~/archive/fit/batch/**/*.fit --fast -D 'Bike=Cotic Soul'
dev/ch2 --dev monitor ~/archive/fit/monitor/*.fit --fast
dev/ch2 --dev monitor ~/archive/fit/batch/**/*.fit --fast
cp ~/.ch2/database.sqlq ~/.ch2/database.sqlq-loaded
dev/ch2 --dev statistics

duration=$(($SECONDS - $start))
echo "$(($duration/60)) min $(($duration%60)) sec"
