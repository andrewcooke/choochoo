
## Latest Changes

See [upgrade
instructions](https://andrewcooke.github.io/choochoo/version-upgrades).

### v0.31.0

Moving towards a more integrated system, building on the modular
components that already exist.  A new command, `upload` copies data to
the `Data.Dir` (a new constant).  The `activities` command can read
from this directory.  Together, this allows the user to upload data
via the (extended) web interface and formalizes 'best practice' use.
Another new command, `upgrade` copies data from a previous install and
replaces the migration scripts.

### v0.30.0

Changed interval handling so that possibly incorrect values are marked
'dirty' rather than deleted immediately.  Added separate activity
groups for road and MTB (see default config).  Added achievements.
Fixed a bunch of bugs introduced in the big changes in the previous
release.

### v0.29.0

Rewrote diary, decoupling model and view, and added web based (React)
view.  See `ch2 web start`.  Re-did activity topics (so old data lost
on upgrade, sorry).  Added support for 'extended' intervals which
allows statistics on 'all time'.

### v0.28.0

Major database changes to allow activity topics and decouple model
and view in diary (which has also been rewritten).  Coverage statistics
and scaling of SHRIMP model when HR data incomplete.  System data in
separate database to allow for commits that don't affect main data.

### v0.27.0

Small change to database schema (removing activity type from
segments).  Fixed power calculations.  Improved docs.

### v0.26.0

Small change to database schema.  Not user-visible, but requires a new
database / minor release.  **Important**: v0.26.0 has incorrect
database name.  Please use 0.26.1.  Sorry :(

### v0.25.0

[Equipment Tracking](https://andrewcooke.github.io/choochoo/kit).
Some database changes (timestamp statistics).

### v0.24.0

Improved support for multiple activities.  FF statistics are
calculated for all activities (together).  Clearer upgrade
instructions.

### v0.23.0

Dropped old notebooks.  Use new templates instead (ch2 jupyter list).

### v0.22.0

HR calculations via data frames.  New pipeline class names - use
dev/reset.sh (modify to get the import paths correct) to rebuild the
database.

### v0.21.0

New Jupyter template some_activities that allows filtering by
statistics.

### v0.20.0

Modified `ch2 fit` to use sub-command syntax (so `ch2 fit records`
instead of `ch2 fit --records`).  This gives more feedback and better
structured help from argparse.  Also, recent code has a bunch of fixes
from user feedback, so it seemed worth making a new minor release.

### v0.19.0

Added composite sources to simplify dependencies between data.  Fixes
problem where multiple statistics pipeline runs were needed to get a
stable system.  Also changed (much of) Jupyter access to data to
construct DataFrames directly from SQL queries - this should give
faster data access, but required that Statistic type was stored in the
StatisticName table (ie that statistics are of a single type, which
wasn't actually required until now).  As always, the database update
script can be found in the `migraine` directory.

### v0.18.0

Major rewrite to import pipelines.  Now use multiple processes where
possible.  Rebuild time for my data, on my machine, cut in half (and
now including power calculations).  Experimented with power
calculations, but "advanced" approach, fitting for wind direction and
speed, didn't give good results (and was slow, hence the rewrite).
Migrate existing databases using `migraine/sqlp2sqlq.sh` (edit the
file, run, and then reload data from FIT files).

### v0.17.0

Added `timestamp` to database which improves / extends logic to avoid
un-needed work re-calcualting statistics.  Migrate existing databases
using `migraine/sqlo2sqlp.sh` (edit the file, run, and then reload
data from FIT files).

### v0.16.0

Diary plots are generated via Jupyter (running an embedded Jupyter
server, generating a notebook, and pushing it to the browser) rather
than Bokeh.  This works round some Bokeh server bugs and serves as a
nice intro to Jupyter.  Cleaned up a lot of the plotting code, too.

### v0.15.0

Modified database schema (`serial` in statistic_journal which makes
time-series logic simpler).  Migrate existing databases using
`migraine/sqln2sqlo.sh` (you will then need to reload data from FIT
files).

### v0.14.0

Zoom in summary plots (embedded Bokeh server while diary is used).

### v0.13.0

Automatic addition of
[elevation](https://andrewcooke.github.io/choochoo/elevation) and
detection of [climbs](https://andrewcooke.github.io/choochoo/docs).

### v0.12.0

Extend `ch2 fix-fit` functionality (can scan a directory and print
file names of god or bad files).  Required a change in parameters -
now you must explicitly add `--fix-header` and `--fix-checksum` if you
want to do that.

### v0.11.0

Parsing of "accumulated" fields in FIT files plus a bunch more fixes
thanks to test data from python-fitparse.

### v0.10.0

Contains a tool to [fix corrupt FIT
files](https://andrewcooke.github.io/choochoo/fix-fit).

### v0.9.0

Choochoo has a [GUI](https://andrewcooke.github.io/choochoo/summary)!!!

### v0.8.0

[Nearby activities](https://andrewcooke.github.io/choochoo/nearby) and
simplified / improved data access in Jupyter.

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
