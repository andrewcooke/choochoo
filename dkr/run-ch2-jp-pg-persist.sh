#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

source version.sh
source timezone.sh

CMD=$0
BIG=
JS=
SLOW=
RESET=0
RESTORE=0
PGCONF=postgres-default.conf
DEV=
DEV2=

help () {
    echo -e "\n  Run choochoo + jupyter + postgres with named volumes"
    echo -e "\n  Usage:"
    echo -e "\n   $CMD [--big] [--slow] [--js] [--reset] [--prof] [--dev] \\"
    echo -e "           [--version VERSION] [-h]"
    echo -e "\n  --big:       use larger base distro"
    echo -e "  --slow:      do not mount pip cache (buildkit)"
    echo -e "  --js:        assumes node pre-built"
    echo -e "  --reset:     re-create the disks"
    echo -e "  --restore:   restore database from backup (you must backup first)"
    echo -e "  --prof:      use the pgbadger conf for postgres (profiling)"
    echo -e "  --dev:       use dev-specific disks"
    echo -e "  --version:   version for kupyter mount ($VERSION)"
    echo -e "   -h:         show this message"
    echo -e "\n  --big, --slow and --js are only used if --reset is specified\n"
    exit 1
}

while [ $# -gt 0 ]; do
    if [ $1 == "--big" ]; then
        BIG=$1
    elif [ $1 == "--slow" ]; then
        SLOW=$1
    elif [ $1 == "--js" ]; then
        JS=$1
    elif [ $1 == "--reset" ]; then
        RESET=1
    elif [ $1 == "--restore" ]; then
        RESTORE=1
    elif [ $1 == "--prof" ]; then
	PGCONF=postgres-pgbadger.conf
    elif [ $1 == "--dev" ]; then
        DEV="-dev"
        DEV2="--dev"
    elif [ $1 == "--version" ]; then
        shift
	VERSION="$1"
    elif [ $1 == "-h" ]; then
        help
    else
        echo -e "\nERROR: do not understand $1\n"
        help
    fi
    shift
done

./prune.sh

rm -f postgres.conf
ln -s $PGCONF postgres.conf

if (( RESET )); then
    ./make-postgresql-data-volume.sh $DEV2
    if [[ ! -z "$DEV" ]]; then
	if (( RESTORE )); then
	    ./restore-pg-persist.sh
	fi
    fi
    ./make-postgresql-log-volume.sh $DEV2
    ./make-choochoo-image.sh $BIG $SLOW $JS $DEV2
    ./make-jupyter-image.sh $SLOW $DEV2
fi

rm -f docker-compose.yml
cp docker-compose-ch2-jp-pg-persist.yml docker-compose.yml
sed -i s/DEV/$DEV/ docker-compose.yml 
sed -i s/VERSION/$VERSION/ docker-compose.yml
docker volume create --name=choochoo-data || true
TZ=$TZ ID="$(id -u):$(id -g)" docker-compose up
