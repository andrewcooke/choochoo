
# Choo-Choo

This is a training diary built around my own needs as an (injured)
cyclist and programmer.

Copyright (c) 2018 Andrew Cooke andrew@acooke.org, GPL v2 licence (see
LICENCE).

## Features

* Simple, quick diary through TUI (Test User Interface) with
  
  * Basic daily stats (resting HR, sleep time, etc)

  * Injury tracking

* Efficient command line interface for basic actions

* Sophisticated schedule engine:

  * Flexible, compact specification of repeating events
  
  * Programmatic generation of training schedules
  
* All data exposed:

  * Simple, normalised SQLite3 schema
  
  * SQLAlchemy object model

## Getting Started

This is very basic, still in development, could break at any point,
and was written to scratch a personal itch rather than be a general
tool.  So I don't promise much.  But if you want to try anyway you
would need to do something like:

* Clone this repo

* Run the `dev/make-env.sh` script to set the Python environment

* Enable the environment with `source env/bin/activate`

* Start the program with `dev/ch2 diary`

It's developed on Linux but with a little care should be
cross-platform.
