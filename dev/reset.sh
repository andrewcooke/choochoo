#!/bin/bash -e

shopt -s globstar
start_all=$SECONDS

echo
echo "resetting database"
start_database=$SECONDS
./ch2/migraine/sqlr2sqlr.sh
cp ~/.ch2/database.sqlr ~/.ch2/database.sqlr-empty
duration=$(($SECONDS - $start_database))
echo "reset finished $(($duration/60)) min $(($duration%60)) sec"

echo
echo "running activities in parallel"
start_activities=$SECONDS
ALL_CPUS="-K cost_calc=100"
(dev/ch2 --dev -v2 activities ~/archive/fit/bike/*.fit --fast -D 'Bike=Cotic Soul'; dev/ch2 --dev -v2 activities ~/archive/fit/batch/**/*.fit --fast -D 'Bike=Cotic Soul' $ALL_CPUS) &
(dev/ch2 --dev -v2 monitor ~/archive/fit/monitor/*.fit --fast; dev/ch2 --dev -v2 monitor ~/archive/fit/batch/**/*.fit --fast $ALL_CPUS) &
wait
cp ~/.ch2/database.sqlr ~/.ch2/database.sqlr-loaded
duration=$(($SECONDS - $start_activities))
echo "activities finished $(($duration/60)) min $(($duration%60)) sec"

echo
echo "running statistics in series"
start_statistics=$SECONDS
dev/ch2 --dev -v2 statistics
cp ~/.ch2/database.sqlr ~/.ch2/database.sqlr-stats
duration=$(($SECONDS - $start_statistics))
echo "statistics finished $(($duration/60)) min $(($duration%60)) sec"

duration=$(($SECONDS - $start_all))
echo
echo "total time $(($duration/60)) min $(($duration%60)) sec"
echo
