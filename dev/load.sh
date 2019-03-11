#!/bin/bash

shopt -s globstar
start=$SECONDS

dev/ch2 --dev activities ~/archive/fit/bike/*.fit --fast -D 'Bike=Cotic Soul'
dev/ch2 --dev activities ~/archive/fit/batch/**/*.fit --fast -D 'Bike=Cotic Soul'
dev/ch2 --dev monitor ~/archive/fit/monitor/*.fit --fast
dev/ch2 --dev monitor ~/archive/fit/batch/**/*.fit --fast

duration=$(($SECONDS - $start))
echo "$(($duration/60)) min $(($duration%60)) sec"
