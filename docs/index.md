
# Getting Started

* [Danger Ahead](#danger-ahead)
* [OS-Specific Instructions](#os-specific-instructions)
  * [Github Codespaces](#github-codespaces)
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
page - currently this project is not easy to use and fixing that is not a high
priority (well, more exactly, it is not a short-term priority).

If you want to continue anyway, the notes below point you in the right
direction. Good luck!

## OS-Specific Instructions

### Github Codespaces

*Warning - Experimental*

If you have access to Github Codespaces, This is the quickest way to get up
and running with a development environment. Clone the Choochoo repo to your
account, select the branch you want to use, and run the "Code -> Open with
Codespaces" flow.  Once in there, open up a terminal and move on to the Ubuntu
instructions.

All of the dependencies are already there and docker is running so you should
skip all of the apt-get commands, but it's likely that that you'll need to
update docker-compose. You may have luck with running:

https://gist.github.com/tylerszabo/b5b3f9874bb9cce56d23e1f814433b86

Once you're up and running, open the "docker" panel, right click on the
running choochoo container, and click "Open in browser".

### MacOS

This has not been run natively on Mac OS X, but you can run an Ubuntu VM using
something like [multipass](http://multipass.run). Ensure that you have enough 
memory (4G) and disk (25G) to run.

`multipass launch -d 25G -m 4G -n choochoo`
`multipass exec choochoo -- apt-get install -y gcc`
`multipass shell choochoo`

Now that you are in your VM, on to the Ubuntu instructions to finish
installation.

To access choochoo once it is running, you will need to set up port forwarding
using something like this from your Mac, where 192.168.64.3 is the ip of your
vm:

`ssh -L 8000:127.0.0.1:8000 ubuntu@192.168.64.3`

### Ubuntu

The following started up the system on an Ubuntu 20 virtual machine (new
install, with only gcc, perl and make already added to support the VirtualBox
client tools):

```
git clone https://github.com/andrewcooke/choochoo.git
cd choochoo
sudo apt-get update

# configure the python environment
sudo apt-get install -y python3.8-venv libpq-dev python3.8-dev
dev/make-env-py.sh

# configure the javascript environment
sudo apt-get install -y npm
dev/make-env-js.sh

# configure docker
sudo apt-get install -y apt-transport-https ca-certificates curl \
     gnupg-agent software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository \
     "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
     $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose
sudo usermod -aG docker $USER

[reboot]

# build and start the docker images (takes a long time)
cd choochoo
FORCE_NEW_DISK=1 dkr/run-ch2-jp-pg-persist.sh --reset

# eventually choochoo is visible at http://0.0.0.0:8000/

Ctrl-C
dkr/run-ch2-jp-pg-persist.sh   # normal use
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
has the latest code).  In the dkr directory are various scripts (in general a
script will display help if given the `-h` argument).

Once (only) you need to create a disk (virtual volume) where the permanent
data (FIT files) are stored:

    FORCE_NEW_DISK=1 dkr/make-choochoo-data-volume.sh

Do not repeat this or you will lose all previous uploads.

Then use `run-ch2-jp-pg-persist.sh` to start everything.  Use `--reset` to
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

## More Information

[Docker Cookbook](docker).

[Technical Documentation](technical).
