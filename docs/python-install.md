
# Python Install

## Python Version

Check you have Python 3.8 or later installed:

    > python --version
    Python 3.8.3

If not, install as appropriate.  On some systems you may need to use
`python3` or `python3.8`.

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

Once installed, continue with [Getting Started](.)
