
# Getting Started

* [Install](#install)
  * [Source](#source)
  * [Package](#package)
  * [Further Reading](#further-reading)
* [Configuration](#configuration)
  * [Default Config](#default-config)
  * [Going Deeper](#going-deeper)

## Install

You can install from source, or use a prepared package.

Choochoo is designed to be modified and extended.  This is easiest to
do if you install from source.

On the other hand, installing a package is slightly easier and you can
switch to using the source later, if necessary.

In both cases you need **Python 3.7** (or later, although I haven't
tested yet with 3.8).  So you may need to get a recent Python version
from [python.org](https://www.python.org/downloads/).

To check your Python version:

    > python --version
    Python 3.7.0

The version shown must be greater than or equal to 3.7.0.

### Source

In a suitable directory, clone the latest source from github:

    git clone git@github.com:andrewcooke/choochoo.git
    
Then you can execute the code within a virtualenv:

    cd choochoo
    dev/make-env-py.sh
    dev/ch2 help

This adds a soft link so that the development code is present in the
Python path (see output from `make-env-py.sh`).

### Package

Alternatively, if you only want to use the code "as is", you can download 
the latest release from Pypi.  It's still worth using a virtualenv:

    python3.7 -m venv env
    source env/bin/activate
    pip install --upgrade pip
    pip install choochoo
    ch2 help

### Further Reading

* [git](https://realpython.com/python-git-github-intro/) - this is a
  general intro to git and github.  You do *not* need to create a
  github account or repository to use Choochoo.

* [virtualenv](https://realpython.com/python-virtual-environments-a-primer/) -
  a virtualenv lets you install a Python program (like Choochoo)
  without it affecting any other Python programs you use.

## Configuration

### Default Config

Once installed the system must be configured.

A basic configuration can be generated with the `config`
command:

    > ch2 config default

(if you are using source you may need to type `dev/ch2` instead of
`ch2` - I'll assume that's obvious from now on).

You can see what that implies by starting the diary:

    > ch2 diary

which will display today's entry.  To quit the diary, type `alt-Q`.
To quit without saving changes, type `alt-X`.

### Going Deeper

Choochoo is very flexible.  You can configure it however you want.
Unfortunately, the process for doing this is rather low-level and
difficult to document precisely.  You can get started with the
following resources:

* [Configuration](configuration) - this describes how to get started
  changing the configuration using Python and SQL.

* Read the source:
  * [My own configuration](https://github.com/andrewcooke/choochoo/blob/master/ch2/config/personal.py)
  * [The default configuration](https://github.com/andrewcooke/choochoo/blob/master/ch2/config/default.py)
  * [Available Python functions](https://github.com/andrewcooke/choochoo/blob/master/ch2/config/database.py)

* [Data Model](data-model) - this describes how the basic concepts in
  Choocho (things like statistics, topics, journals) are represented
  in the database.  Once you understand the details here the links
  above may appear less like "magic" and more like logical procedures.

* [Training Plans](training-plans) - these are added in the same way
  as other diary fields.
