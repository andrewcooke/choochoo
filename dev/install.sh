#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
VM=0
PROFILE=
BACKUP=

help () {
    echo -e "\n  Install after initial checkout\n"
    echo -e "  Usage:\n"
    echo -e "    $CMD [--vm] [--profile PROFILE] [--backup BACKUP] [-h]"
    echo -e "    --vm:       installing inside a virtual machine"
    echo -e "    --profile:  create a new empty profile in the database"
    echo -e "    --backup:   restore the database from the given backup"
    echo -e "    -h:         show this message"
    echo -e "\n"
    exit 1
}

while [ $# -gt 0 ]; do
    case $1 in
	-h)
	    help
	    ;;
	--vm)
	    VM=1
	    ;;
	--profile)
	    shift
	    PROFILE=$1
	    ;;
	--backup)
	    shift
	    BACKUP=$1
	    ;;
	*)
	    echo -e "\nERROR: do not understand $1"
	    exit 2
	    ;;
    esac
    shift
done

if [ ! -z "$PROFILE" -a ! -z "$BASCKUP" ]; then
    echo -e "\nERROR: Specify only one of --profile and --backup"
    exit 3
fi

if [ $VM -eq 1 ]; then
    if [ ! -e ~/.ch2 ]; then
	echo -e "\nERROR:"
	echo -e "The ~/.ch2 directory does not exist"
	echo -e "Mount a shared volume from the parent file system"
	exit 4
    fi
    if [ ! `id -nGz $USER | tr '\0' '\n' | grep '^vboxsf$'` ]; then
	sudo usermod -a -G vboxsf $USER
	echo -e "\nWARNING: Log off and on again to activate new vbboxsf group membership"
    fi
fi

if [ ! `id -nGz $USER | tr '\0' '\n' | grep '^docker$'` ]; then
    sudo usermod -a -G docker $USER
    echo -e "\nERROR: Log off and on again to activate new docker group membership"
    exit 5
fi

pushd .. >& /dev/null

dev/make-env-py.sh
dev/package-profile.sh
dev/package-bundle.sh

touch dkr/auto-prune

dkr/make-images.sh --dev
dkr/make-postgresql-data-volume.sh --dev

if [ ! -z "$BACKUP" ]; then
    dkr/restore-pg-persist.sh --dev $BACKUP
fi

if [ ! -z "$PROFILE" ]; then
    dkr/run-pg-persiste.sh --dev &
    sleep 15
    source py/env/bin/activate
    ch2 db add user
    ch2 db add database
    ch2 db add profile "$PROFILE"
    docker stop postgresql
fi
