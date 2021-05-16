#!/bin/bash

if [ -f auto-prune ]; then
    docker container prune -f
    docker image prune -f
# no!  cleans out the cache!!
#    docker system prune -f
else
    echo "prune manually or \`touch auto-prune\`"
fi
