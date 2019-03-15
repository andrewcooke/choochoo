#!/bin/bash

kill -9 `ps aux | grep "ch2" | grep -v grep | awk '{ print $2 }'`
