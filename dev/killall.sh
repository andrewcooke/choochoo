#!/bin/bash

kill -9 `ps aux | grep "ch2" | awk '{ print $2 }'`
