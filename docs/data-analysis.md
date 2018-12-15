
# Data Analysis

Below I focus on data access via [pandas](https://pandas.pydata.org/)
and [Jupyter](http://jupyter.org/) - this will let you read,
manipulate and plot data within your web browser.

Plotting packages in Python - especially for maps - seem to be
unreliable, so the emphasis here is on providing the data in a
standard format.  Hopefully you can then display that data with
whatever you find works for you.  Current examples use
[Bokeh](https://bokeh.pydata.org/) and
[Matplotlib](https://matplotlib.org/).

All Choochoo's data (all *your* data) are stored in an SQLite3 file at
`~/.ch2/database.sql?` (the final character changes with database
schema version).  So you can also use any programming language with an
SQLite binding (for Python the `ch2.squeal.tables` package contains a
[SQLAchemy](https://www.sqlalchemy.org/) ORM mapping).

  * [Starting Jupyter](#starting-jupyter)
  * [Accessing Data](#accessing-data)
    * [Session](#session)
    * [SQLAlchemy ORM Query](#sqlalchemy-orm-query)
    * [DataFrames](#dataframes)
    * [Waypoints](#waypoints)
  * [Plotting Data](#plotting-data)
  * [Summary](#summary)
  * [Examples](#examples)

## Starting Jupyter

I use Jupyter as the environment, because it's pretty and little extra
work over pure python.  All that is necessary, assuming that Choochoo
is installed (and you have activated the virtualenv, if necessary), is
typing

    jupyter notebook
    
which should display a window in your web browser.  There you can load the
examples from the `notebooks` directory.

## Accessing Data

Pandas works with `DataFrame` objects, while Choochoo stores data in
an SQLite database with SQLALchemy ORM mapping.  Fortunately these
technologies work well together.  The learning curve is fairly steep,
but the result is very flexible access to the data.

### Session

To connect to the database we need a session:

    In[] > from ch2.data import *
           s = session('-v4')

where the `session` function takes arguments similar to `ch2 no-op` on
the command line.

### SQLAlchemy ORM Query

Using the session we can extract data from the database as Python
objects.  In practice (see below) we will not use these objects
directly.  Instead we will wrap the data in DataFrames.  But we will
use the same SQLAlchemy queries.  This lets us use all the power of
SQL to make conditional queries across multiple tables of data.

Our basic tools are:

  * The [Data Model](data-model), which is embodied in the [table
    classes](https://github.com/andrewcooke/choochoo/tree/master/ch2/squeal/tables)
  * The [SQLAlchemy Query
    API](http://docs.sqlalchemy.org/en/latest/orm/query.html)

Using these we can, for example, see all **StatisticName** instances
that have units of "bpm":

    In[] > from ch2.squeal import *
           names = s.query(StatisticName). \
                     filter(StatisticName.units == 'bpm').all()
           str(names[0])    
    '"Rest HR" (Topic/Topic "Diary" (d))'

### DataFrames

The same data can be retrieved as a DataFrame using the `df` function:

    In[] > names = df(s.query(StatisticName).
                        filter(StatisticName.units == 'bpm'))
           names
    [...table of information...]

For example, in a new Python 3 notebook:

    from ch2.data import data
    d = data('-v 0')
    d.statistics()

will show a list of the statistics available.

You may want to revise the [data model](data-model) at this point.

The `ch2.data.database.Data` instance provides access to:

### Waypoints

It is sometimes useful to access the sequence of data associated with
an **ActivityJournal**.  This information is spread across multiple
**StatisticJournal** entries, but can be extracted as a single
DataFrame using the `waypoints` function:

    In[] > from ch2.lib.date import to_time
           aj = s.query(ActivityJournal). \
                  filter(ActivityJournal.start > to_time('2017-08-21'),
                         ActivityJournal.finish < to_time('2017-08-22')).one()
           w = waypoints(aj.id, 'Latitude', 'Longitude', Heart Rate')

The example above finds the **ActivityJournal** for a given day and
then retrieves the associated GPS and HRM data in a time-indexed
table.

## Plotting Data

For examples of how to plot this data see:

* The Jupyter notebooks in the `notebooks` directory - these use Bokeh.
* The code in `tests/test_data.py` - these use Matplotlib.

A few helper routines are available in `ch2.data.plot` to help massage the
data into the correct format.

## Summary

To analyse data you will probably work as follows:

  * Find where the data are stored in the database.  To do this,
    consult the [Data Model](data-model) document, examine the [table
    classes](https://github.com/andrewcooke/choochoo/tree/master/ch2/squeal/tables),
    or look at similar wotk in the `notebooks` directory.
  * Create a [session](#session) in [Jupyter](#starting-jupyter).
  * Use a [SQLAlchemy ORM Query](#sqlalchemy-orm-query) to extract the
    data from the database.
  * Wrap the data in a DataFrame using `df`.
  * Plot the data with Bokeh.

## Examples

These are taken from the Jupyter notebooks described above.  Obviously results
depend on the data entered into the system.

![](distance.png)

![](summary.png)
