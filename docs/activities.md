
# Activities

## Introduction

Activities are defined in FIT files (from, for example, a Garmin
watch).  To examine a FIT file see [here](fit-files).

More precisely, the day-to-day details are **ActivityJournal**
entries, which are grouped by an **ActivityGroup** (which might be
cycling, running, etc).

Some statistics (distance, time, fastest time over certain common
distances, etc) are calculated for each activity.  In addition,
summary statistics (ranking, best etc) are also calculated.  These are
defined using [**Schedule**s](scheduling) (the default configuration
being per-month and per-year)

## Contents

* [Defining Activities](@defining-activities)
* [Adding Activities](#adding-activities)
* [Calculating Summary Statistics](#calculating-summary-statistics)
* [Both](#both)
* [FTHR](#fthr)
* [Timespans](#timespans)

## Defining ActivityGroups

ActivityGroups are defined during [configuraton](configuration).  The
defaults are `Bike` and `Run`.

## Adding Activities

After a ride (or run, or whatever) download your FIT file to somewhere
on disk and give it a unique name (I name mine by date with an extra
short code that roughly indicates route).  *You need to save (archive)
these* as they are the raw data your training is based on and must be
re-read when Choochoo is updated.

Once you have the FIT file, you can import it into Choochoo with the
command

    ch2 add-activity Cycling /path/to/FIT/file
    
where "Cycling" is the Activity name defined earlier.

The path can also be to a directory, in which case all files will be read.

By default, only "new" files (based on path and last-modified date) are
read.  Adding the `-f` flag forces all files to be (re-)read:

    chs add-activity Cycling /path/to/dir -f
    
In addition, the `-f` flag crates the activity (eg Cycling) if it doesn't
exist.

## Calculating Summary Statistics

The commands

    ch2 add-summary --month
    ch2 add-summary --year
    
will add summary statistics for the month or year (only one set can exist at
a time - yearly replace monthly, etc).

By default only "missing" statistics are calculated.  Use `-f` to recalculate all
values.

## Both

It is possible to calculate summary statistics when reading activities by
adding `--month` or `--year` to the `add-activity` command.  For example:

    ch2 add-activity Cycling /path/to/FIT/file --month
    
## FTHR

Some of the statistics require heart rate zones.  Currently these are defined
via FTHR using the command

    ch2 add-fthr FTHR [DATE]
    
where `FTHR` is the value (bpm) and `DATE` is the start date for validity.

The zones are calculated using the British Cycling zones (taken from their
online calculator).

A possible estimator for your FTHR is the "Max med HR over 30m" statistic.
This is the maximum value found for the median heart rate over 30 minutes in
ride (so the heart rate for the entire ride is median filtered with a 30 minute
window and then the maximum value taken).

## Timespans

The format in which activity data are stored in the database may need a 
little explanation.  They are grouped into "timespans", where a single
timespan contains data between pauses in the FIT stream (ie laps or
auto-pausing at road junctions etc).

Some statistics are "aware" of timespans.  For example, "Active Time" 
is the total time *within* timespans - it excludes pauses.  Similarly
the "Max med" heart rate statistics (see [above](#fthr)) exclude gaps
above a certain threshold (this is to avoid many short, intense intervals
appearing as a single, long period of intense activity).
