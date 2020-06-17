
# Getting Started

## Docker

The most reliable way to try Choochoo is via
[Docker](https://docs.docker.com/get-docker/).  Once you have Docker
installed run:

    > docker run -p 127.0.0.1:8000:8000 -p 127.0.0.1:8001:8001 \
      --shm-size 1g andrewcooke/choochoo:latest

This will download and run the latest stable image.  Once running
(download could take some time) you can see the web interface at
[http://localhost:8000](http://localhost:8000).

## Python Install

Alternatively you can do the traditional [Python
install](python-install).  This is more likely to give problems,
*especially on platforms other than Linux*.  For a first look, I
recommend Docker.

Check you have Python 3.7 or later installed:

    > python --version
    Python 3.7.4

If not, install as appropriate.  On some systems you may need to use
`python3` or `python3.7`.

## Create a Virtual Environment

We will install all Python dependencies in a virtual environment so
that they are independet from other Python programs.

This will create a directory called `env` in the current directory.
You can create this wherever you want, and give it whatever name you
want, as long as you change the commands that follow appropriately.

    > python -m venv env
    > source env/bin/activate

Note: the `venv` package is part of standard Python, but it seems that
on some operating systems it may need to be installed separately (eg
by installing the package python-venv).

## Install Choochoo

    > pip install choochoo

## Start the Web Server

    > ch2 web start

Here, if you give `--base DIR`, then data will be stored in `DIR`.
Otherwise, it is stored in `.ch2` in your home directory.

## Initial Configuration

Within the web site (which should have opened in your brower), select
`Configure/Initial` in the left-hand menu.  Read the page and then,
hopefully, click `CONFIGURE`.

## Upgrade User Data

If you have a previous install you can copy across data to the new
version via the `Configure/Upgrade` page.

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

[Technical documentation](technical)
