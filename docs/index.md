
# Getting Started

## Sorry

See the [explanation](https://github.com/andrewcooke/choochoo) on the front
page - currently this project is not easy to use and fixing that is not a
high priority.

If you want to continue anyway, the notes below point you in the right
direction.  You need a unix machine and it's likely macos won't cut it.

## Docker

The system runs within docker.  It requires three images and three virtual
volumes.

Clone the repo (the master branch is more likely to work, but the dev branch
has the latest code).  In the dkr directory are some scripts:

* make-choochoo-image.sh - use this to build the main image (the other images
  run postgres and jupyter and are downloaded automatically).

* run-ch2-jp-pg-persist.sh - use this to start everything.  Use `-h` to see
  options.  Use `--reset` to build disks for the first use.

The `run-ch2-jp-pg-persist.sh` script will start the web server on
http://localhost:8000

## Initial Configuration

Within the web site select `Configure/Initial` in the left-hand menu.
Read the page and then, hopefully, click `CONFIGURE`.

## Upgrade User Data

If you have a previous install (not the case with the basic Docker
demo) you can copy across data to the new version via the
`Configure/Upgrade` page.

## Constants

On `Configure/Constants` you can edit various system constants.  For
now, apart from FTHR values and the Garmin username / password (if you
want to download monitor data), you probably want to leave these
alone.

## Upload

Once the system is configured you can upload activity data (FIT files)
via the `Upload` page.  If you are just starting, ignore `Kit` for the
moment, select a file, and click `UPLOAD`.

## More Information

[Docker Cookbook](docker).

[Technical Documentation](technical).
