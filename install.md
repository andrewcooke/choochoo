
# Install

This describes how I install the current development system.

    > dkr/make-images.sh
    > dkr/make-postgresql-log-volume.sh --dev
    > dkr/make-postgresql-data-volume.sh --dev

At this point you may want to copy from backups of the `~/.ch2` directory and
the Postgres volume.  Then run

    > dkr/run-ch2-jp-pg-persist.sh --dev
    
