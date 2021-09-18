#!/bin/bash

#killall.sh
#shutdown.sh

#ch2 db remove schema
ch2 db remove database
ch2 db add database
ch2 db add profile acooke
ch2 import
ch2 --dev upload

