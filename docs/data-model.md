
# Data Model

## Introduction

Choochoo is all about the data - getting statistics that you can
analyze and use to improve performance.  The data model is a key part
of this: we need a model that is flexible enough to capture anything
that might be important, simple enough that analysis doesn't have many
special cases, and reliable enough to avoid errors.

## Contents

* [Concepts](#concepts)
  * [Statistics](#statistics)
  * [Sources](#sources)
* [Implementation](#implementation)
  * [Inheritance](#inheritance)
  * [Correctness](#correctness)
  * [Events](#events)
  * [Rules](#rules)
  * [Hard Reset](#hard-reset)
* [Data Input](#data-input)
  * [Schedules](#schedules)
  * [Topics](#topics)

## Concepts

### Statistics

A **Statistic** is a simple thing - a name with units.  For example,
"Rest HR/bpm".  In practice it also has a description and some
"metadata" for display, tracking who is responsible for creating new
values, etc.

For a Statistic to be useful it must be associated with some values.
More exactly, it must have entries in the **StatisticJournal** which
associated values with **Source**s.

There are three types of StatisticJournal, for values that are
integers, floats and text.

It will be convenient later to divide Statistics into two kinds:

1. Raw statistics that are entered into the system from outside:
   values entered into the diary, values read from a FIT file, or
   "constants" entered by the user from the command line.

2. Derived statistics that are calculated from other, pre-existing
   statistics.

(A careful reader may have noted that the above statements use
"statistic" to refer to *values*, which are actually stored in the
StatisticJournal.  This is why I used "statistic" with a lower case
"s" - when I am referring to a particular table I will revert to
capitalized names.)

Many statistics also have ranking and percentile information.  These
behave similarly to derived statistics (they are associated with
Interval Sources), but are stored separately.

### Sources

Sources are, well, the sources of statistics - where the values come
from.

There are several different Sources:

* **Activities** are read from FIT files and provide a wealth of
  statistics (note that the GPS trace, HR time series, etc, are not
  stored as statistics themselves, but values calculated from these,
  like time in HR zones, total distance, are).

* **Topics** are used to structure entries in the diary and can be
  associated with statistics that are entered by the user (depending
  on the details of configuration).

* **Intervals** in time are used as sources for derived statistics.
  This may sound odd, but it helps avoid stale data (see below).  An
  Interval has a start time and a duration - typically a day, month or
  year.  So the total distance cycled over May 2018, for example, is a
  derived statistic whose source is the interval covering that month.

* **Monitor** is similar to an Activity - it is read from FIT files -
  but is background "wellness" data (rest HR, steps walked, etc).
  (Dirty implementation detail: Monitor data are recorded at random
  times throughout the day so the system also calculates a daily
  value (total steps, lowest rest HR) and associates this with an
  Interval corresponding to that day.)

As with Statistics and the StatisticJournal, the data associated with
these Activities, Topics and Monitor are stored in
**ActivityJournal**, **TopicJournal** and **MonitorJournal**.

Every Source has an associated time - this is also the time for the
statistic.

## Implementation

### Inheritance

The use of inheritance in the database schema is driven by the need to balance
flexibility - a variety of different types and structures - with "freshness" -
it must be simple to "expire" stale data.  The former pushes towards many
types; the latter towards few types connected by "on delete cascade".
Inheritance resolves this conflict by associating multiple types with a single
(base) table.

For more details on inheritance and the SQLAlchemy approach used, please see
[Joined Table
Inheritance](https://docs.sqlalchemy.org/en/latest/orm/inheritance.html#joined-table-inheritance)
in the SQLAlchemy docs.

Two inheritance hierarchies are used, for Source and StatisticJournal.  In
both cases the structure is very simple, with all concrete classes being
direct children of the base.

Source has four children: Interval, ActivityJournal, TopicJournal and
**Constant** (arbitrary values entered by the user, but not on a
scheduled basis - FTHR, for example).

StatisticJournal has three children: **StatisticJournalInteger**,
**StatisticJournalFloat** and **StatisticJournalText** - used for
storing values of the respective types.  StatisticJournal has a
foreign key relationship with Source, so that when a Source is deleted
the corresponding statistics are deleted (via cascade).

### Correctness

It is important that the data in the StatisticJournal are correct.  To ensure
this we must consider what happens when data are inserted, updated and
deleted:

* Insertions into StatisticJournal are associated with the appropriate Source.
  Amongst other things, this gives the time for the StatisticJournal entry.
  New values may invalidate some derived statistics, so any insertion must
  have a corresponding deletion of associated Intervals.

* Updates to StatisticJournal may invalidate some derived statistics, so any
  insertion must have a corresponding deletion of associated intervals.

* Deletions from Source will cascade into deletions from StatisticJournal.
  This may invalidate some derived statistics, so any insertion must have a
  corresponding deletion of associated intervals.

The above is true for both raw and derived statistics (since Intervals are
Sources).

### Events

The above "deletion of associated intervals" can be automated within
SQLAlchemy using the `before_flush()` hook.  Whenever the database is going to
be modified (via the ORM) we can check and automatically delete appropriate
Intervals.

In addition, the association of statistics with TopicJournal entries
is peformed by an event-driven callback.

### Rules

Following from the above, we have the following rules that must be followed:

* Do not delete from StatisticJournal directly.  Delete Sources.

* Do not delete Sources via SQL.  Delete at the object level (within
  SQLAlchemy).  This is required for two reasons:

  1. So that the entire hierarchy is removed.  See `test_inheritance.py` for
     justification.

  2. So that automatic deletion of Intervals can be triggered.

Together these allow us to calculate derived statistics only when needed (ie
when an Interval is missing).

### Hard Reset

Following the rules above allows us to (efficiently) calculate only *missing*
derived statistics.  In practice it will also be useful to have the option of
deleting all derived statistics (by deleting all Intervals).

## Data Input

### Schedules

Schedules do not have their own table in the database (they are part of
Topics, see below), but play an important role in the diary.

A schedule is a specification for a repeating event within a certain date
range.  An example would be

    2018-09-29/2w[1mon,2wed]2018-01-01-2019-01-01

which "reads" as "the first monday and second wednesday of each fortnight (2
weeks) in 2018 (the time range at the end), shifted so that 2018-09-29 occurs
in the first week)".

TODO - check shifting implementation.

For a more precise definition see the code in `ch2.lib.schedule`.

### Topics

Direct data input, via the diary, is structured with Topics.  These are
categories, with a tree-like structure, that are scheduled to appear at
certain times.

A Topic can be associated with various Statistics (via
**TopicFields**).  The appropriate StatisticJournal entries can then
be read and modified within the diary.

Configuration of this is necessarily quite complex, but a default
configuration is provided with Choochoo.

Example Topics include:

* Simple diary entries (mood, weather, sleep tracking).  In this case the
  schedule is daily with open range.

* Injuries and medication.  In this case the schedule will have the range of
  the injury and, for a particular medicine or treatment, might be on certain
  days.

* Training plans.  In this case the tree structure of Topics is
  important and individual entries may be for only a single day.

## Timezones

All the above was written assuming that all calculations are in UTC.
This was an oversight.  In fact, diary-related presentation is
(obviously!) timezone-specific.

This is a problem.  Some data are timezone-specific and some not.  How
do we handle this?

First, we need to identify which data vary with timezone.  In
particular, which Sources.

* Topic entries come from the diary.  These need to be saved (from the
  diary, when values are changed) and retrieved (for display in the
  diary).  What happens when the timezone changes?

* Intervals should also depend on the timzeone.  This doesn't matter
  so much for long (eg yearly) intervals, but for daily intervals, we
  want to use the local definition of "day".

* Constants may be a small issue, in that we users will assume they
  are entering local date.  But only conversion on input is needed.

Other than Sources, most data seem to work fine in UTC.  In
particular, data obtained from FIT files can be converted to UTC (some
care is needed with handling cumulative steps which accumulate
throughout a local day).

### Intervals

The Schedule class works internally with dates (not times).  If we
convert this to times using the local timzone then logic should remain
consistent (nothing in the code assumes particular alignment except
when using values derived from Schedule methods).

There *is* going to be a problem if the timzone changes - existing
Intervals will no longer be found at the "right" times.  But all
Intervals are derived data and so can be recalculated in this case (eg
if the user moves location).

Steps to change:

* Remove implicit conversion from date to time.

* Subclass Schedule to include methods that are timezone aware and do
  conversions.

* Finally implement MonitorSteps correctly.

* Get tests running (maybe add new tests).

### Topics

Diary entries, etc (plans, injuries, ...).

We need to worry about:

* Retrieving saved data for the correct day if timestamps change.

* Deleting appropriate Intervals when data change.

* Calculating values using Intervals.

To fix the first of these we either need to save the date in the
database or use some convention like always use UTC date.  But always
using UTC date will affect Interval calculations - the `time` field
must be usable by Interval calculation.

So it seems that we need:

* An additional field for TopicJournal, which is date.

* The time should be set to the start of the local day (in UTC) so
  that Interval calulations work.

* When the user changes timezone retrieval will still work correctly
  (using the date field), but time values will be wrong and Interval
  calculations will be broken.  All I can think of here is that we
  auto-detect timzeone changes and trigger fix-up (wipe Intervals and
  set time to correct value based on date).

* To auto-detect timezone data we need to store timezone in the
  database.



