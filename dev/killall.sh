#!/bin/bash

kill -9 `ps aux | grep "ch2" | grep -v grep | grep -v docker | awk '{ print $2 }'`
