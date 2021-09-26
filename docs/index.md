ch2# Getting Started

* [Danger Ahead](#danger-ahead)
* [OS-Specific Instructions](#os-specific-instructions)
  * [Linux (OpenSuse)](#linux-opensuse)
  * [MacOS](#macos)
  * [Windows](#windows)
* [General Guidance](#general-guidance)
* [Initial Configuration](#initial-configuration)
  * [Upgrade User Data](#upgrade-user-data)
  * [Constants](#constants)
  * [Upload](#upload)
* [More Information](#more-information)

## Danger Ahead

See the [explanation](https://github.com/andrewcooke/choochoo) on the front
page - currently this project is not easy to use and fixing that is not a high
priority (well, more exactly, it is not a short-term priority).

If you want to continue anyway, the notes below point you in the right
direction. Good luck!

## OS-Specific Instructions

### Linux (OpenSuse)

I use OpenSuse Leap 15.3 for development, within a VirtualBox VM.  On my main
(host) machine I have a `~/.ch2` directory and a directory containing my FIT
files from Garmin.  I mount these on the VM client.

After checking the project out from github I use `dev/install.sh` to install
the development system.  Then the system can be started (in docker) with

    > dkr/run-ch2-jp-pg-persist.sh --dev -G vboxsf

(the `-G vboxsf` changes the group to allow reading the files mounted from the
host on VirtualBox).

The GUI should then be visible at http://localhost:8000

If this does not work check the output from `install.sh` carefully.  There is
probably an error somewher due to a missing dependency.

It is also possible to start the database alone in docker and run the web
server locally (useful for debugging, but ni Jupyter):

    > dev/run-pg-persist.sh --dev &
    > source py/env/bin/activate
    > ch2 web service

### MacOS

This has not been run natively on Mac OS X, but you can run an Ubuntu VM using
something like [multipass](http://multipass.run) to run an OpenSuse image
(then follow the instructions above).

### Windows

No idea.  Sorry.

## General Guidance

The system runs within docker.  It requires three images and two virtual
volumes.  The permanent data are stored at `~/.ch2` and mapped into docker.

Clone the repo (the master branch is more likely to work, but the dev branch
has the latest code).  In the dkr directory are various scripts (in general a
script will display help if given the `-h` argument).

Do not repeat this or you will lose all previous uploads.

Use `run-ch2-jp-pg-persist.sh` to start everything.  Use `--reset` to
build disks (virtual volumes) for the first use.

    dkr/run-ch2-jp-pg-persist.sh --reset

It will start the web server on http://localhost:8000

## Initial Configuration

Within the web site select `Configure/Initial` in the left-hand menu.
Read the page and then, hopefully, click `CONFIGURE`.

### Upgrade User Data

If you have a previous install (not the case with the basic Docker
demo) you can copy across data to the new version via the
`Configure/Upgrade` page.

### Constants

On `Configure/Constants` you can edit various system constants.  For
now, apart from FTHR values and the Garmin username / password (if you
want to download monitor data), you probably want to leave these
alone.

### Upload

Once the system is configured you can upload activity data (FIT files)
via the `Upload` page.  If you are just starting, ignore `Kit` for the
moment, select a file, and click `UPLOAD`.

