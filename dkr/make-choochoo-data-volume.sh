#!/bin/bash

CMD=$0
DEV=

help () {
    echo -e "\n  Create a data volume for choochoo data"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--dev] [-h]"
    echo -e "\n  --dev:       dev-specific"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "--dev" ]; then
        DEV="-dev"
    elif [ $1 == "-h" ]; then
        help
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

./prune.sh

docker volume rm -f "choochoo-data$DEV"
docker volume create "choochoo-data$DEV"

docker run --rm \
       -v "choochoo-data$DEV":/data \
       opensuse/leap \
       mkdir -p /data/permanent/srtm1
docker run --rm \
       -v "choochoo-data$DEV":/data \
       -v ~/.ch2/permanent/srtm1:/srtm1 \
       opensuse/leap \
       cp /srtm1/S34W071.SRTMGL1.hgt.zip \
          /srtm1/S34W072.SRTMGL1.hgt.zip \
          /data/permanent/srtm1/
docker run --rm \
       -v "choochoo-data$DEV":/data \
       -v ~/.ch2:/ch2 \
       opensuse/leap \
       cp -rv /ch2/permanent/monitor /data/permanent/
docker run --rm \
       -v "choochoo-data$DEV":/data \
       -v ~/.ch2:/ch2 \
       opensuse/leap \
       cp -rv /ch2/permanent/activity /data/permanent/

source version.sh

if [ -e ~/.ch2/$VERSION ]; then
    docker run --rm \
	   -v "choochoo-data$DEV":/data \
	   -v ~/.ch2:/ch2 \
	   opensuse/leap \
	   cp -rv /ch2/$VERSION /data/
fi
if [ -e ~/.ch2/$VERSION_1 ]; then
    docker run --rm \
	   -v "choochoo-data$DEV":/data \
	   -v ~/.ch2:/ch2 \
	   opensuse/leap \
	   cp -rv /ch2/$VERSION_1 /data/
fi
docker run --rm \
       -v "choochoo-data$DEV":/data \
       opensuse/leap \
       mkdir -p /data/$VERSION/notebook

docker volume ls
