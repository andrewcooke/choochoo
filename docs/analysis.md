
# Analysis

## Introduction

This documentation focuses on simple, direct (but also limited) data access 
via [pandas](https://pandas.pydata.org/) and [Jupyter](http://jupyter.org/) - 
this will let you read, manipulate and plot data within your web browser.

Plotting packages in Python - especially for maps - seem to be unreliable,
so the emphasis here is on providing the data in an agnostic way.  Hopefully
you cna then display that data with whatever you find works for you.
Current examples use [Bokeh](https://bokeh.pydata.org/) and
[Matplotlib](https://matplotlib.org/).

All Choochoo's data (all *your* data) are stored in an SQLite3 file at 
`~/.ch2/database.sql?` (the final character changes with database
schema version).  So you can also use any programming language with an 
SQLite binding (for Python the `ch2.squeal.tables` package contains a
[SQLAchemy](https://www.sqlalchemy.org/) ORM mapping).

## Contents

* [Starting Jupyter](starting-jupyter)
* [Accessing Data](accessing-data)
* [Plotting Data](plotting-data)
* [Examples](examples)

## Starting Jupyter

We use Jupyter as the environment, because it's pretty and little extra work
over pure python.  All that is necessary, assuming that Choochoo is installed,
is typing

    jupyter notebook
    
which should display a window in your web browser.  There you can load the
examples from `ch2/data/notebooks`.

## Accessing Data

Data are accessed via the `ch2.data.data()` function, which returns a
`ch2.data.database.Data` instance.  Data associated with a particular
activity type are then selected using the `.activity(...)` method (see
`.activity_names()` for available activity types).

The `ch2.data.database.ActivityData` instance provides access to:

* **Activity Statistics** - these are measures calculated for each activity
  diary entry (eg each bike ride).  For example, the total time active.
  The statistic names are available from `.statistics(...)` and the
  `.activity_statistics()` method returns a pandas DataFrame containing data
  for the given statistic(s) for each diary entry.
  
* **Summary Statistics** - these are calculated regularly (eg once per
  month) and summarise the activity statistics mentioned above.  The
  `.summary_statistics(...)` method returns a pandas DataFrame containing a
  tuple of values for each statistic.  This tuple has the min, max and quartile
  values for the given period.
  
* **Activity Diary** - these are the values imported from the FIT file for
  the activity diary entry (eg position, heart rate, etc).  The available
  diary entries are listed in `.activity_diary_names()` and the 
  `.activity_diary(...)` method returns, for a *single* name, a set of DataFrames
  that contain data for each timespan (eg lap, or data between auto-pauses).
  Note that the `x` and `y` columns contain data in "web coordinates" suitable
  for plotting on Google Maps etc.   
  
In addition, the `Data` instance provides direct access to:

* **Diary Data** - these are the values in the diary entries (mood, resting 
  heart rate, etc).  The `.diaries()` method returns a DataFrame with all data.
  
* **Injury Data** - these are the "pain" scores and notes for each injury.
  The available injuries are listed by `.injury_names()` and the DataFrames
  provide via a map (dct) from name to frame via `.injuries(...)`.

The various methods above that take a name can typically take a list
of names (comma separated or as separated arguments) and regular expressions.
This can lead to some confusion if the name contains characters with special 
meaning for regexps (in particular parentheses).

DataFrames usually have the date / time information as index.

## Plotting Data

To see examples of how to plot this data see:

* The Jupyter notebooks in `ch2/data/notebooks` - these use Bokeh.
* The code in `tests/test_data.py` - these use Matplotlib.

A few helper routines are available in `ch2.data.plot` to help massage the
data into the correct format.

## Examples

These are taken from the Jupyter notebooks described above.  Obviously results
depend on the data entered into the system.

![](distance.png)

![](summary.png)
