
# Getting Started

* [Install](#install)
  * [Source](#source)
  * [Package](#package)
  * [Further Reading](#further-reading)

## Install

You can install from source, or use a prepared package.

Choochoo is designed to be modified and extended.  This is easiest to
do if you install from source.

On the other hand, installing a package is slightly easier and you can
switch to using the source later, if necessary.

In both cases you need **Python 3.7**.  So you may need to get the
latets Python version from
[python.org](https://www.python.org/downloads/).

To check your Python version:

    > python --version
    Python 3.7.0

The version shown must be greater than or equal to 3.7.0.

### Source

In a suitable directory, clone the latest source from github:

    git clone git@github.com:andrewcooke/choochoo.git
    
Then you can execute the code within a virtualenv:

    cd choochoo
    dev/make-env.sh
    dev/ch2 help

If you are not making frequent changes to the code you may want to
install it within the virtualenv:

    dev/install-in-env.sh
    source env/bin/activate
    ch2 help
    
(you will need to re-install whenever you alter the code).

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

* virtualenv](https://realpython.com/python-virtual-environments-a-primer/)
  - a virtualenv lets you install a Python program (like Choochoo)
  without it affecting any other Python programs you use.

## Configuration

Once installed the system must be [configured](configure).
