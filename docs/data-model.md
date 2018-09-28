
# Data Model

## Introduction

Choochoo is all about the data.  In particular - getting statistics that you
can analyse and use to improve performance.  The data model is a key part of
this.  We need a model that is flexible enough to capture anything that might
be important, simple enough that analysis doesn't have many special cases, and
reliable enough to avoid errors.

## Contents

## Concepts

### Statistics

A Statistic is a fairly simple thing - basically a name with (optional) units
and description (in practice they also have "metadata" for display, tracking
who is responsible for creating new values, etc).  For a Statistic to be
useful it must be associated with some values.  More exactly, it must be
associated with entries in the StatisticJournal - each entry combines a
(double) value with a time and a Source.

There are two kinds of Statistic, which are distinguished by their Sources
(more on those below):

1. Raw statistics are entered into the system from outside.  For example,
   values entered into the diary, or values read from a FIT file.

2. Derived statistics are calculated from other, pre-existing statistics.

(A careful reader may have noted that the above statements use "statistic" to
refer to *values*, which are actually stored in the StatisticJournal.  This is
why I used "statistic" with a lower case "s" - when I am referring to a
particular table I will revert to capitalized names.)

Many statistics have ranking and percentile information.  These behave
similarly to derived statistics (they are associated with Interval Sources),
but are stored separately.

### Sources

There are several different Sources:

* Activities are read from FIT files and provide a wealth of statistics (note
  that the GPS trace, HR time series, etc, are not stored as statistics
  themselves, but values calculated from these, like time in HR zones, total
  distance, are).

* Topics are used to structure entries in the diary and can be associated with
  statistics that are entered by the user (depending on the details of
  configuration).

* Intervals in time are used as sources for derived statistics.  This may seem
  somewhat abstract, but it helps avoid stale data (see below).  An Interval
  has a start time and a duration - typically a day, month or year.  So the
  total distance cycled over May 2018, for example, is a derived statistic
  whose source is the interval covering that month.

As with Statistics and the StatisticJournal, the data associated with these
Activities and Topics are stored in ActivityJournal and TopicJournal (the
Activity and Topic tables store metadata).

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
in the SQLALchemy docs.

A single inheritance hierarchy is used, with Source as the base type, and
three children: Interval, ActivityJournal, and TpicJournal.  StatisticJournal
has a foreign key relationship with Source, so that when a Source is deleted
the corresponding statistics are deleted (via cascade).

### Correctness

It is important that the data in the StatisticJournal are correct.  To ensure
this we must consider what happends when data are inserted, updated and
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

The above "deletoin of associated intervals" can be automated within
SQLAlchemy using the `before_flush()` hook.  Whenever the database is going to
be modified (via the ORM) we can check and automatically delete appropriate
Intervals.

### Rules

Following from the above, we have the following rules that must be followed:

* Do not delete from StatisticJournal directly.  Delete Sources.

* Do not delete Sources via SQL.  Delete at the object level (within
  SQLAlchemy).  This is required for two reasons:

  1. So that the entire hierarchy is removed.  See `test_inheritance.py` for
     justification.

  2. So that automatic delteion of Intervals can be triggered.

### Hard Reset

Following the rules above allows us to (efficiently) calculate only *missing*
derived statistics.  In pratice it will also be useful to have the option of
deleting all derived statistics (by deleting all Intervals).
