
# Configure

## Introduction

Choochoo is configured via the database.  This is most easily done by
running Python commands, either via a script or at the command line.

The price of a flexible system is complexity.  To understand things
completely you will need to understand the [data model](data-model),
but I've also tried to provide some simplified short-cuts and defaults
that should ease the pain.

In the examples that follow I will use the Python command line
directly.  Using a script is similar and, because you can delete the
database and re-run the script until debugged, more useful in
practice.

## Connecting to the Database

    > python                               
    Python 3.7.0 (default, Aug 20 2018, 18:32:46)
    [GCC 7.3.1 20180323 [gcc-7-branch revision 258812]] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from ch2.config import *
    >>> log, db = config('-v 5')
    INFO: Using database at ...
    >>>

The `config()` command above takes command line arguments similar to
`ch2` (space-separated or in separate strings) and returns a log (from
the standard python logging library; more useful in scripts) and a
database connection.

## The Default Configuration

A default is pre-packaged and easy to apply:

    >>> default(db)
    >>>

It is worth comparing the [source for the
default](https://github.com/andrewcooke/choochoo/blob/master/ch2/config/default.py)
with the results:

### Constants

    > ch2 constant
    INFO: Using database at ...

    FTHR.Bike: Heart rate at functional threshold (cycling). See https://www.britishcycling.org.uk/knowledge/article/izn20140808-Understanding-Intensity-2--Heart-Rate-0

    FTHR.Run: Heart rate at functional threshold (running).

The command above lists the available constants.  These are values
that you can provide at the command line.  For example:

    > ch2 constant --set FTHR.Bike 154

These constants are defined in the
[source](https://github.com/andrewcooke/choochoo/blob/master/ch2/config/default.py)
with `add_activity_constant()`.  This takes a reference to an
activity, defined with `add_activity()`.  If you are unsure what an
activity is, now is the time to study the [data model](data-model).

### Topics and Statistics

    > ch2 diary

TODO

## Later Modifications

Remember that it's easy to create a backup just by copying your
database file.

### Adding A Field

    > sqlite3 ~/.ch2/database.sqlj 'select * from topic_field join statistic_name on statistic_name_id = statistic_name.id'

    > python <<EOF
    from ch2.config.database import config, add_topic_field
    from ch2.squeal.tables.topic import Topic
    from ch2.uweird.fields import Text
    log, db = config('-v 5')
    with db.session_context() as s:
	diary = s.query(Topic).filter(Topic.name == 'Diary').one()
	add_topic_field(s, diary, 'Route', 90, display_cls=Text)
    EOF

### Changing Field Order

    > sqlite3 ~/.ch2/database.sqlj 'select * from topic_field join statistic_name on statistic_name_id = statistic_name.id'
    > sqlite3 ~/.ch2/database.sqlj 'update topic_field set sort=-1 where sort=70'
    > sqlite3 ~/.ch2/database.sqlj 'update topic_field set sort=70 where sort=80'
    > sqlite3 ~/.ch2/database.sqlj 'update topic_field set sort=80 where sort=-1'

