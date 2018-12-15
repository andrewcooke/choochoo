
# Choochoo (ch2)

An **open**, **hackable** and **free** training diary.

Please see the [full
documentation](https://andrewcooke.github.io/choochoo/).  This page
contains only:

* [Technical Overview](#technical-overview)
* [Latest Changes](#latest-changes)

## Technical Overview

All data are stored in an SQLite database (SQLAlchemy ORM interface).
The schema separates "statistics" (named time series data) from the
source (which might be direct entry, read from a FIT file, or
calculated from pre-existing values).

The "diary" view, where the user enters data, is itself generated from
the database.  So the fields displayed (and the statistics collected)
can be customized.  This configuration can include "schedules" which
control when information is displayed (eg: weekdays only; every other
day; second Sunday in the month).

The combination of customizable diary fields and scheduling allows
training plans to be entered and displayed.

Customization (fields, training plans, etc) must be done via Python or
SQL.  There is no graphical user interface for configuration.  This
presents a steep learning curve but is ultimately very flexible -
"any" training plan can be accommodated.  Python code for generating
example plans is included (see package `ch2.config.plan`).

Data are processed via "pipelines".  These are Python classes whose
class names are also configured in the database.  Existing pipelines
calculate statistics from FIT file data, recognise segments from GPS
endpoints, and generate summaries (eg monthly averages).

A Python interface allows data to be extracted as DataFrames for
analysis in Jupyter workbooks (or dumping to stdout).  So general
Python data science tools (Pandas, Numpy, etc) can be used to analyze
the data.  Example workbooks are included in the source.

The data are stored in an "open" format, directly accessible by third
party tools, and easily backed-up (eg by copying the database file).
When the database format changes scripts are provided to migrate
existing data (see package `ch2.migraine`).

Support libraries include FIT file parsing and spatial R-Trees.

Currently the program is single-user (ie the data in the database are
not grouped by user).  Multiple users can co-exist using separate
database files.

*Choochoo collects and organizes time-series data using
athlete-appropriate interfaces.  It facilitates calculations of
derived statistics and extraction of data for further analysis using
Python's rich data science tools.  Both data and code are open and
extensible.*

## Latest Changes

### v0.7.0

[Segments](https://andrewcooke.github.io/choochoo/segments).

### v0.6.0

Impulse calculations.  Faster importing and statistics.  See [Scaled
Heart Rate Impulse -
SHRIMP](https://andrewcooke.github.io/choochoo/impulse)

### v0.5.0

More readable database (using text instead of opaque numerical hashes
in a couple of places).  Faster database loading of activity and
monitor data.  Time is now directly present in the statistic journal
table, along with all activity and monitor data (no separate data
tables).  This enables TSS calculation (next version).

### v0.4.0

Tidied lots of rough corners, improved docs, added examples, download
from Garmin Connect.  This could probably be used by 3rd parties.

### v0.3.0

Diary now uses dates (rather than datetimes) and is timezone aware
(Previously all times were UTC datetimes; now data related to the
diary - like statistics calculated on daily intervals - use the date
and the local timezone to convert to time.  So, for example, stats
based on monitor data are from your local "day" (midnight to
midnight)).

Monitor data from FIT files can be imported.

### v0.2.0

Major rewrite to generalize the database schema.  Moved a lot of
configuration into the database.  Now much more flexible, but less
interactive.
