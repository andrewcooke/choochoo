
# Choochoo (ch2)

An **open**, **hackable** and **free** training diary.

Please see the [full
documentation](https://andrewcooke.github.io/choochoo/).  This page
contains only some images and a [Technical
Overview](#technical-overview).

The following plots are generated automatically from the diary -
clicking a "link" starts Jupyter and pushes the page to the browser.
The pages can be edited and serve as an introduction to accessing the
data manually.

![](docs/graphic-summary.png)

![](docs/graphic-similarity.png)

## Technical Overview

The system includes:

* An SQLite3 database containing time series data.

* An interface to move data between the database and Pandas
  DataFrames.

* A FIT reader to import new data.

* Algorithms to derive new statistics from the data (using Pandas for
  efficiency).

* Pipelines to apply the algorithms to new data on import (in parallel
  processes for efficiency).

* An embedded Jupyter server to explore the data.

* Pre-written scripts to present graphical data views via Jupyter.

* A "diary" to present textual data and allow data entry.

The database has an SQLAlchemy ORM interface.  The schema separates
"statistics" (named time series data) from the source (which might be
direct entry, read from a FIT file, or calculated from pre-existing
values).  SQL tracks dependencies to avoid stale values.

The pipelines are Python classes whose class names are also configured
in the database.

The data are stored in an "open" format, directly accessible by third
party tools, and easily backed-up (eg by copying the database file).
When the database format changes scripts are provided to migrate
existing data (see package `ch2.migraine`).  Data extracted from FIT
files are *not* migrated - they must be re-imported.

Support libraries include: FIT file parsing; spatial R-Trees; reading
elevation data from SRTM files; estimating power from elevation and
speed; Fitness / Fatigue models; detection of pre-defined segments;
clustering of routes; climb detection.

The "diary" view, where the user enters data, is also configured via
the database.  So the fields displayed (and the statistics collected)
can be customized.  This configuration can include "schedules" which
control when information is displayed (eg: weekdays only; every other
day; second Sunday in the month).

The combination of customizable diary fields and scheduling allows
training plans to be entered and displayed.  This presents a steep
learning curve but is ultimately very flexible - "any" training plan
can be accommodated.  Python code for generating example plans is
included (see package `ch2.config.plan`).

Currently the program is single-user (ie the data in the database are
not grouped by user).  Multiple users can co-exist using separate
database files.

*Choochoo collects and organizes time-series data using
athlete-appropriate interfaces.  It facilitates calculations of
derived statistics and extraction of data for further analysis using
Python's rich data science tools.  Both data and code are open and
extensible.*
