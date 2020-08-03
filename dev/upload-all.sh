#!/bin/bash

shopt -s globstar

#dev/ch2 upload --no-process --kit cotic /archive/fit/bike/cotic/*.fit
#dev/ch2 upload --no-process --kit bowman /archive/fit/bike/bowman/*.fit
#dev/ch2 upload --no-process /archive/fit/bike/uk/*.fit
#dev/ch2 upload --no-process /archive/fit/monitor/*.fit
dev/ch2 upload --no-process /archive/fit/batch/**/*.fit
