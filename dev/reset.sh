#!/bin/bash

shopt -s globstar

#./ch2/migraine/sqlo2sqlp.sh
#cp /home/andrew/.ch2/database.sqlp /home/andrew/.ch2/database.sqlp-empty
cp /home/andrew/.ch2/database.sqlp-empty /home/andrew/.ch2/database.sqlp
dev/ch2 --dev activities ~/archive/fit/bike/*.fit --fast
dev/ch2 --dev activities ~/archive/fit/batch/**/*.fit --fast
dev/ch2 --dev monitor ~/archive/fit/monitor/*.fit --fast
dev/ch2 --dev monitor ~/archive/fit/batch/**/*.fit --fast
dev/ch2 --dev statistics


