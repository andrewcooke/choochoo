#!/bin/bash

./prune.sh
docker volume rm -f choochoo-data
docker volume create choochoo-data
docker run --rm \
       -v choochoo-data:/data \
       opensuse/leap \
       mkdir -p /data/permanent/srtm1
docker run --rm \
       -v choochoo-data:/data \
       -v ~/.ch2/permanent/srtm1:/srtm1 \
       opensuse/leap \
       cp /srtm1/S34W071.SRTMGL1.hgt.zip \
          /srtm1/S34W072.SRTMGL1.hgt.zip \
          /data/permanent/srtm1/
docker run --rm \
       -v choochoo-data:/data \
       -v ~/.ch2:/ch2 \
       opensuse/leap \
       cp -rv /ch2/permanent/monitor /data/permanent/
docker run --rm \
       -v choochoo-data:/data \
       -v ~/.ch2:/ch2 \
       opensuse/leap \
       cp -rv /ch2/permanent/activity /data/permanent/
docker run --rm \
       -v choochoo-data:/data \
       -v ~/.ch2:/ch2 \
       opensuse/leap \
       cp -rv /ch2/0-33 /data/
docker volume ls

