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

if [ $DELETE -eq 1 -o ! -e ~/bin/kops ]; then
    curl -Lo kops https://github.com/kubernetes/kops/releases/download/$(curl -s https://api.github.com/repos/kubernetes/kops/releases/latest | grep tag_name | cut -d '"' -f 4)/kops-linux-amd64
    chmod +x ./kops
    sudo mv ./kops ~/bin
fi

if [ $DELETE -eq 1 -o ! -e ~/bin/kubectl ]; then
    curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
    chmod +x ./kubectl
    sudo mv ./kubectl ~/bin
fi

popd

source ../py/env/bin/activate
pip install awscli
