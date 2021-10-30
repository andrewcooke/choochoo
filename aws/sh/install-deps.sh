#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0
DELETE=0

help() {
    echo -e "\n  Install tools needed for AWS to ~/bin\n"
    echo -e "  Usage:"
    echo -e "    $CMD [-h] [--delete]\n"
    echo -e "  -h:       show this text"
    echo -e "  --delete: delete existing install\n"
    exit 1
}

while [[ $# -gt 0 ]]; do

    case $1 in
	-h)
	    help
	    ;;
	--delete)
	    DELETE=1
	    ;;
	*)
	    echo -e "\nERROR: did not understand $1"
	    exit 2
	    ;;
    esac
    shift
    
done

if [ ! -e ~/bin ]; then
    echo -e "\nERROR: ~/bin does not exist"
    exit 3
fi

pushd /tmp >& /dev/null

if ! command -v aws &> /dev/null ; then
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
fi

popd
