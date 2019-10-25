#!/bin/bash -e

shopt -s globstar
start_all=$SECONDS

VERSION=`grep 'CH2_VERSION =' ch2/commands/args.py | sed -e "s/.*CH2_VERSION = '\([0-9]\+\.[0-9]\+\).*/\1/"`
VERSION=`echo $VERSION | sed -e s/\\\\./-/g`

echo
echo "resetting database $VERSION"
dev/ch2 -v1 jupyter stop
sleep 3
start_database=$SECONDS
"./ch2/migraine/reload/$VERSION.sh"
cp ~/.ch2/"database-$VERSION.sql" ~/.ch2/"database-$VERSION-empty.sql"
duration=$(($SECONDS - $start_database))
echo "reset finished $(($duration/60)) min $(($duration%60)) sec"

echo
echo "running activities in parallel"
start_activities=$SECONDS
ALL_CPUS="-K cost_calc=100"
(dev/ch2 --dev -v2 activities ~/archive/fit/bike/*.fit --fast -D 'Bike=Cotic Soul'; dev/ch2 --dev -v2 activities ~/archive/fit/walk/*.fit --fast; dev/ch2 --dev -v2 activities ~/archive/fit/batch/**/*.fit --fast -D 'Bike=Cotic Soul' -D 'kit=cotic' $ALL_CPUS) &
(dev/ch2 --dev -v2 monitor ~/archive/fit/monitor/*.fit --fast; dev/ch2 --dev -v2 monitor ~/archive/fit/batch/**/*.fit --fast $ALL_CPUS) &
wait
cp ~/.ch2/"database-$VERSION.sql" ~/.ch2/"database-$VERSION.sql-loaded"
duration=$(($SECONDS - $start_activities))
echo "activities finished $(($duration/60)) min $(($duration%60)) sec"

echo
echo "running statistics in series"
start_statistics=$SECONDS
dev/ch2 --dev -v2 statistics
cp ~/.ch2/"database-$VERSION.sql" ~/.ch2/"database-$VERSION-stats.sql"
duration=$(($SECONDS - $start_statistics))
echo "statistics finished $(($duration/60)) min $(($duration%60)) sec"

duration=$(($SECONDS - $start_all))
echo
echo "total time $(($duration/60)) min $(($duration%60)) sec"
echo
