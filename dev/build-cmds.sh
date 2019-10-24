#!/bin/bash

rm -f docs/command-summary.md

cat > docs/command-summary.md <<EOF

# Command Summary

EOF

COMMANDS=`dev/ch2 -h | grep '{' | head -1 | sed -e 's/ *[{}] *//g'`

IFS=','; for cmd in $COMMANDS; do
    echo "* [$cmd](#$cmd)" >> docs/command-summary.md
done

IFS=','; for cmd in $COMMANDS; do
    echo $cmd
    echo >> docs/command-summary.md
    dev/ch2 help $cmd | cut -c 2- >> docs/command-summary.md
done

