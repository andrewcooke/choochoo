#!/bin/bash

#./ch2/migraine/sqln2sqlo.sh
./ch2/migraine/sqlo2sqlo.sh
dev/ch2 --dev activities ~/archive/fit/bike/*.fit --fast
dev/ch2 --dev activities ~/archive/fit/batch/**/*.fit --fast
dev/ch2 --dev monitor ~/archive/fit/monitor/*.fit --fast
dev/ch2 --dev statistics


