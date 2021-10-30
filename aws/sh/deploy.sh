
#!/bin/bash

cd "${BASH_SOURCE%/*}/" || exit

CMD=$0

help() {
    echo -e "\n  Deploy ch2 to AWS\n"
    echo -e "  Usage:"
    echo -e "    $CMD [-h]\n"
    echo -e "  -h:       show this text\n"
    exit 1
}

while [[ $# -gt 0 ]]; do

    case $1 in
	-h)
	    help
	    ;;
	*)
	    echo -e "\nERROR: did not understand $1"
	    exit 2
	    ;;
    esac
    shift
    
done

set -e

export AWS_PAGER=
ami-04213e43c6566adf7
#aws ec2 describe-vpcs
#aws ec2 create-vpc --cidr-block 10.0.0.0/28
