
VERSION=`grep 'CH2_VERSION =' ../py/ch2/commands/args.py | sed -e "s/.*'\([0-9]\+\.[0-9]\+\.[0-9]\+\)'.*/\1/" | cut -d '.' -f 1-2 | sed -e s/\\\\./-/`
MAJOR=`echo $VERSION | cut -d '-' -f 1`
MINOR=`echo $VERSION | cut -d '-' -f 2`
VERSION_1="$MAJOR-$(($MINOR-1))"
VERSION_2="$MAJOR-$(($MINOR-2))"
