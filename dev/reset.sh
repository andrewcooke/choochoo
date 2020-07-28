#!/bin/bash

dev/killall.sh
dev/shutdown.sh

dev/ch2 db remove schema
dev/ch2 db remove database
dev/ch2 db add database
dev/ch2 db add profile acooke
dev/ch2 import
dev/ch2 --dev upload

