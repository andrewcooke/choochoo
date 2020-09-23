#!/bin/bash

CMD=$0

help () {
    echo -e "\n  Create a data volume for choochoo data"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--dev] [-h]"
    echo -e "   -h:         show this message\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "-h" ]; then
        help
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

# delete this is you really want to
echo "refusing to delete existing data"

./prune.sh

docker volume rm -f "choochoo-data"
docker volume create "choochoo-data"

docker run --rm \
       -v "choochoo-data":/data \
       opensuse/leap \
       mkdir -p /data/permanent/srtm1
docker run --rm \
       -v "choochoo-data":/data \
       -v ~/.ch2/permanent/srtm1:/srtm1 \
       opensuse/leap \
       cp /srtm1/S34W071.SRTMGL1.hgt.zip \
          /srtm1/S34W072.SRTMGL1.hgt.zip \
          /data/permanent/srtm1/
docker run --rm \
       -v "choochoo-data":/data \
       -v ~/.ch2:/ch2 \
       opensuse/leap \
       cp -rv /ch2/permanent/monitor /data/permanent/
docker run --rm \
       -v "choochoo-data":/data \
       -v ~/.ch2:/ch2 \
       opensuse/leap \
       cp -rv /ch2/permanent/activity /data/permanent/

source version.sh

if [ -e ~/.ch2/$VERSION ]; then
    docker run --rm \
	   -v "choochoo-data":/data \
	   -v ~/.ch2:/ch2 \
	   opensuse/leap \
	   cp -rv /ch2/$VERSION /data/
fi
if [ -e ~/.ch2/$VERSION_1 ]; then
    docker run --rm \
	   -v "choochoo-data":/data \
	   -v ~/.ch2:/ch2 \
	   opensuse/leap \
	   cp -rv /ch2/$VERSION_1 /data/
fi
docker run --rm \
       -v "choochoo-data":/data \
       opensuse/leap \
       mkdir -p /data/$VERSION/notebook
docker run --rm \
       -v "choochoo-data":/data \
       opensuse/leap \
       chown -R $(id -u):$(id -g) /data

docker volume ls
