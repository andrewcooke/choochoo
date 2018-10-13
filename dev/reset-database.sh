#!/bin/bash

rm -fr ~/.ch2/database.sqls
dev/ch2 example-config
dev/ch2 constant --set FTHR.Bike 154
dev/ch2 activity Bike "~/archive/fit/2018-*.fit"
