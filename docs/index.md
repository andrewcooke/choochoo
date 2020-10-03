
# Getting Started

* [Danger Ahead](#danger-ahead)
* [OS-Specific Instructions](#os-specific-instructions)
  * [MacOS](#macos)
  * [Ubuntu](#ubuntu)
  * [Other Linux](#other-linux)
  * [Windows](#windows)
* [General Guidance](#general-guidance)
* [Initial Configuration](#initial-configuration)
  * [Upgrade User Data](#upgrade-user-data)
  * [Constants](#constants)
  * [Upload](#upload)
* [More Information](#more-information)

## Danger Ahead

See the [explanation](https://github.com/andrewcooke/choochoo) on the front
page - currently this project is not easy to use and fixing that is not a
high priority.

If you want to continue anyway, the notes below point you in the right
direction.  You need a unix machine and it's likely macos won't cut it.

## OS-Specific Instructions

### MacOS

Chris Kelly [reports](https://github.com/andrewcooke/choochoo/issues/54) some
success using multipass to run Ubuntu.  See below for updated instructions on
running in Ubuntu.

### Ubuntu

The following started up the system on an Ubuntu 20 virtual machine (new
install, with only gcc, perl and make already added to support the VirtualBox
client tools):

```
git clone https://github.com/andrewcooke/choochoo.git
cd choochoo

# configure the python environment
sudo apt-get install python3.8-venv libpq-dev python3.8-dev
dev/make-env-py.sh

# configure the javascript environment
sudo apt-get install npm
dev/make-env-js.sh

# configure docker
sudo apt-get install apt-transport-https ca-certificates curl \
     gnupg-agent software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository \
     "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
     $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose
sudo usermod -aG docker $USER

[reboot]

# build and start the docker images (takes a long time)
cd choochoo
FORCE_NEW_DISK=1 dkr/run-ch2-jp-pg-persist.sh --reset

# eventually choochoo is visible at http://0.0.0.0:8000/
```

### Other Linux

See Ubuntu above.  Other than installing different packages, it *should* work
(I develop in OpenSuse).

### Windows

No idea.  Sorry.

## General Guidance

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

## More Information

[Docker Cookbook](docker).

[Technical Documentation](technical).
