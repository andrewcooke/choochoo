
This directory contans various scripts related to running ch2 in a
Docker container.  More exactly, running the ch2 process in one
container, a Postgres database in another, and storing the data on two
separate named volumes (one for the Postgres database and another for
the base directory where the system database, files and logs are
stored).

All scripts should be run from inside this directory.

create-ch2-img.sh - create an image containing the ch2 code

create-disk-vol.sh - create an named volume for the disk data.
create-pg-vol.sh - create an named volume for the postgres database

docker-compose-full.yml - config for system with volumes
run-full.sh - run system with volumes

docker-compose-local.yml - config for system with local files
run-local.sh - run system with local files

Note that when the syetem is stoppped the containers are still stored
on disk (`docker container ls -a`).  They are not nedeed (all state is
in the volumes) so can be removed with 'docker container prune').

run-ch2.sh - run a ch2 container (without postgres database)
run-pg.sh - run a postgres container

run-ch2-bash.sh - open a bash session on a running ch2 container
run-pg-bash.sh - open a bash session on a running postgres container
run-psql.sh - open a psql session on a running postgres container
