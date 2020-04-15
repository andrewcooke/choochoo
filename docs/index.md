
# Getting Started

## Python Install

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

## Install Choochoo

    > pip install choochoo

## Start the Web Server

    > ch2 web start

Here, if you give `--base DIR`, then data will be stored in `DIR`.
Otherwise, it is stored in `.ch2` your home directory.

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
