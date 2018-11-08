
# Training Plans

This is where making Choochoo programmable by end users really comes
into its own.  Take a look at [this
code](https://github.com/andrewcooke/choochoo/blob/master/ch2/config/plan/british.py)
defining a training plan taken from British Cycling.  It's simple,
declarative code.  You can add your own.

There are also some simple built-in plans available.

* [Configuration](#configuration)
  * [Topics](#topics)
  * [Schedules](#schedules)
  * [Helper Classes](#helper-classes)
* [Existing Plans](#existing-plans)
* [Adding Your Own](#adding-your-own)

## Configuration

Adding a training plan is similar to [configuring](configuration)
fields for the diary - both use the same basic concepts.

As with configuration, this is done in Python.  A connection to the
database can be made with:

    > python                               
    Python 3.7.0 (default, Aug 20 2018, 18:32:46)
    [GCC 7.3.1 20180323 [gcc-7-branch revision 258812]] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from ch2.config import *
    >>> log, db = config('-v 5')
    INFO: Using database at ...
    >>>

### Topics

Entries in the diary are arranged by "topic".  These have a
hieracrhical (tree-like) structure - and topic can have many child
topics.

You can add parent and child topics with `add_topic()` and
`add_child_topic()` which are both defined in
[ch2.config.database](https://github.com/andrewcooke/choochoo/blob/master/ch2/config/database.py).

### Schedules

[Schedules](schedules) restrict topics to particular dates.  In this
way a training plan can have topics that change by day.

### Helper Classes

The `Week` and `Day` classes in
[ch2.config.plan.weekly](https://github.com/andrewcooke/choochoo/blob/master/ch2/c\
onfig/plan/weekly.py) help you define training plas in a declaritive
way.  See, for example,
[twelve_week_improver()](https://github.com/andrewcooke/choochoo/blob/master/ch2/config/plan/british.py).

## Existing Plans

Two basic plans are pre-defined in
[ch2.config.exponential](https://github.com/andrewcooke/choochoo/blob/master/ch2/config/exponential.py).
These let you define a plan that increases by a fixed (relative)
distance or time on each date.

To define a plan that increases distance by 5% every other day,
starting at 20km on 2018-10-01 and continuing for 2 months, you would
do something like:

    > python                               
    Python 3.7.0 (default, Aug 20 2018, 18:32:46)
    [GCC 7.3.1 20180323 [gcc-7-branch revision 258812]] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from ch2.config import *
    >>> log, db = config('-v 5')
    INFO: Using database at ...
    >>> from ch2.config.plan import *
    >>> plan = exponential_distance('My Plan', '2d', 20, 5, '2018-10-01', '2m')
    >>> plan.create(log, db)
    >>>

## Adding Your Own

Please submit pull requests with plans you add.  Together we can build
a big, useful library.
