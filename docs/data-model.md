
# Data Model

Choochoo is all about the data - getting statistics that you can
analyze and use to improve performance.  The data model is a key part
of this: we need a model that is flexible enough to capture anything
that might be important, simple enough that analysis doesn't have many
special cases, and reliable enough to avoid errors.

* [Concepts](#concepts)
  * [Statistics](#statistics)
  * [Sources](#sources)
* [Implementation](#implementation)
  * [Inheritance](#inheritance)
  * [Correctness](#correctness)
  * [Events](#events)
  * [Rules](#rules)
* [Data Input](#data-input)
  * [Schedules](#schedules)
  * [Topics](#topics)
* [Timezones](#timezones)

## Concepts

### Statistics

A **StatisticName** is a simple thing - a name with units.  For
example, "Rest HR/bpm".  In practice it also has a description and
some "metadata" for display, tracking who is responsible for creating
new values, etc.

For a StatisticName to be useful it must be associated with some
values.  More exactly, it must have entries in the
**StatisticJournal** which associated values at particular times with
**Sources**.

There are four types of StatisticJournal, three for values that are
integers, floats and text, and one that has no value but is simply a
marker that an incident occured - a timestamp.

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

Note that when using Python and SQLAlchemy you do not need to know
what kind of statistic journal you are requesting from the database.
You can query the base class (`StatisticJournal`) and will receive the
appropriate subclass (`StatisticJournalInteger`,
`StatisticJournalFloat`, etc).

### Sources

Sources are where the statistics come from.

There are many different Sources:

* **Activities** are read from FIT files and provide a wealth of
  statistics (both raw - like the GPS data - and derived - like the
  total distance).

* **Monitor** is similar to an Activity - it is read from FIT files -
  but is background "wellness" data (rest HR, steps walked, etc).
  (Dirty implementation detail: Monitor data are recorded at random
  times throughout the day so the system also calculates a daily
  value (total steps, lowest rest HR) and associates this with an
  Interval corresponding to that day.)

* **Topics** are used to structure entries in the diary and can be
  associated with statistics that are entered by the user (depending
  on the details of configuration).

* **Intervals** in time are used as sources for derived statistics.
  This may sound odd, but it helps avoid stale data (see below).  An
  Interval has a start time and a duration - typically a day, month or
  year.  So the total distance cycled over May 2018, for example, is a
  derived statistic whose source is the interval covering that month.

* **Constants** can be set from the command line using the `ch2
  constants` command.  They represent configuration values that rarely
  change (your FTHR, for example).

* **Segments** are used-defined paths that are matched against
  activities.  When an activity matches a segment statistics like the
  time for that segment are recorded.

* **Models** and **Items** are used in kit tracking.  Statistics
  associated with these record their use.

* **Composite** are 'meta' sources that are used to combine other
  sources.  For example, the statistics associated with kit use for a
  particular activity has both Item and Activity sources.

As with Statistics and the StatisticJournal, the data associated with
some sources are stored in journals - **ActivityJournal**,
**TopicJournal**, etc (the data are not the statistics themselves but
additional metadata, like the date of the activity).

## Implementation

### Inheritance

The use of inheritance in the database schema is driven by the need to
balance flexibility - a variety of different types and structures -
with "freshness" - it must be simple to "expire" stale data.  The
former pushes towards many types; the latter towards few types
connected by "on delete cascade".  Inheritance resolves this conflict
by associating multiple types with a single (base) table.

For more details on inheritance and the SQLAlchemy approach used,
please see [Joined Table
Inheritance](https://docs.sqlalchemy.org/en/latest/orm/inheritance.html#joined-table-inheritance)
in the SQLAlchemy docs.

Two inheritance hierarchies are used, for Source and StatisticJournal.
In both cases the structure is relatively simple, with all concrete
classes being direct children of the base.

### Correctness

It is important that the data in the StatisticJournal are correct.  To ensure
this we must consider what happens when data are inserted, updated and
deleted:

* Insertions into StatisticJournal are associated with the appropriate Source.
  New values may invalidate some derived statistics, so any insertion must
  have a corresponding deletion of associated Intervals.

* Updates to StatisticJournal may invalidate some derived statistics, so any
  insertion must have a corresponding deletion of associated Intervals.

* Deletions from Source will cascade into deletions from
  StatisticJournal.  This may invalidate some derived statistics, so
  any deletion must have a corresponding deletion of associated
  Intervals.

* Deletions of Composite source components do not cascade
  (unfortunately).  So `Composite.clean()` must be called manually
  whenever Composite sources are modified.

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

  1. So that the entire hierarchy is removed (this would be OK if the
  Source parent was deleted - children would be deleted by cascade -
  but not if the child was deleted).

  2. So that automatic deletion of Intervals can be triggered.

* Call `Composite.clean()` when necessary.

Together these allow us to calculate derived statistics only when needed (ie
when an Interval is missing).

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

For a more precise definition see the code in `ch2.lib.schedule` and
the [Schedule documentation](schedules).

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

Some data are timezone-specific (eg diary entries and intervals) and
some not.  This is reflected in the different database types used for
date / time values.

The current timezone is stored in the database.  If this changes then
Intervals are deleted and the associated dderived statistics
re-calculated.
