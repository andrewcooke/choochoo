
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

## More Here

This doc in development; I need to do an initial release of 0-31 to
write more.

## More Information

[Technical documentation](technical)
