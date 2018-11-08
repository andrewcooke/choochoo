#!/bin/bash

rm -f docs/command-summary.md

echo > docs/command-summary.md <<EOF

# Command Summary

EOF

COMMANDS='activities constants default-config diary fit garmin help monitor statistics no-op package-fit-profile test-schedule'

for cmd in $COMMANDS; do
    echo "* [$cmd](#$cmd)" >> docs/command-summary.md
done

for cmd in $COMMANDS; do
    echo $cmd
    echo >> docs/command-summary.md
    dev/ch2 help $cmd | cut -c 1- >> docs/command-summary.md
done

