
# Docker Scripts

There's a lot of confusion and mess and evolution here.

But basically it's evolving towards three use cases:

* day-to-day use for analysis:

    run-ch2-jp-pg-persist.sh

* development use direct from the source

    run-pg-persist.sh

* development use in an environment closer to deploy (ie with jupiter)

    run-ch2-jp-pg-persist.sh --dev

To support this there are three sets of docker volumes:

  * The data directories used by choochoo (typically mounted as /data
    in an image or at ~/.ch2 - see linking below).

  * The data directories used by postgres for storing the database.

  * The log directory used by postgres.

In addition, the postgres volumes come in two 'flavours' - for normal use and
development.  This means that you don't have to delete the main database when
testing development code.

## Local Data

It is convenient for the choochoo data volume to also be visible at ~/.ch2 so
that `run-pg-persist.sh` and `run-ch2-jp-pg-persist.sh` can access the same
directories.  To do this I soft-link the two:

  ln -s /var/lib/docker/volumes/choochoo-data/_data ~/.ch2

To make this work with unix permissions you will also need to add the
use-level execute bit to intermediate directories in the path.  As far as I
can tell, docker does not care (but this may have security implications if you
are not using a private machine).

## Pruning

The scripts will automatically delete unused contains and images if the file
`auto-prune` exists:

  touch auto-prune

