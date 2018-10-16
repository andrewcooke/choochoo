
# Install

## Development

The "big idea" behind Choochoo is that it's extensible.  *You* can
modify the code to make it work how *you* want.  So I would suggest
installing from github:

    git clone git@github.com:andrewcooke/choochoo.git
    
and then executing the code within a virtualenv:

    cd choochoo
    dev/make-env.sh
    dev/ch2 help
    
If you are not making frequent changes to the code you may want to
install it within the virtualenv:

    dev/install-in-env.sh
    source env/bin/activate
    ch2 help
    
(you will need to re-install whenever you alter the code).

## From Pypi

Alternatively, if you only want to use the code "as is", you can download 
the latest release from Pypi.  It's still worth using a virtualenv:

    virtualenv -p python3.7 env
    source env/bin/activate
    pip install --upgrade pip
    pip install choochoo
    ch2 help

## Configuration

Once installed the system must be [configured](configure).
