#!/bin/bash

rm -fr ~/.ch2/database.sqls
dev/ch2 --dev example-config
dev/ch2 --dev constant --set FTHR.Bike 154
dev/ch2 --dev activity Bike "~/archive/fit/2018-*.fit"
