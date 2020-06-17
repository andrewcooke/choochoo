
# Getting Started

## Docker

The most reliable way to try Choochoo is via
[Docker](https://docs.docker.com/get-docker/).  Once you have Docker
installed run:

    > docker image pull andrewcooke/choochoo:latest
    > docker run -p 127.0.0.1:8000:8000 -p 127.0.0.1:8001:8001 \
      andrewcooke/choochoo:latest

This will download and run the latest stable image.  Once running
(download could take some time) you can see the web interface at
[http://localhost:8000](http://localhost:8000).

## Python Install

Alternatively you can do the traditional [Python
install](python-install).  This is more likely to give problems,
*especially on platforms other than Linux*.  For a first look, I
recommend Docker.

You can also build from
[source](http://github.com/andrewcooke/choochoo), but then you're on
your own (hint: look in the dev directory).

## Initial Configuration

Within the web site (which should have opened in your brower), select
`Configure/Initial` in the left-hand menu.  Read the page and then,
hopefully, click `CONFIGURE`.

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

[Docker Configuration](docker).

[Technical Documentation](technical).
