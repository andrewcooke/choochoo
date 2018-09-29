
# Data Model

## Introduction

Choochoo is all about the data.  In particular - getting statistics that you
can analyze and use to improve performance.  The data model is a key part of
this.  We need a model that is flexible enough to capture anything that might
be important, simple enough that analysis doesn't have many special cases, and
reliable enough to avoid errors.

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

A **Statistic** is a simple thing - a name with (optional) units and
description (in practice they also have "metadata" for display, tracking who
is responsible for creating new values, etc).  For a Statistic to be useful it
must also be associated with some values.  More exactly, it must be associated
with entries in the **StatisticJournal** - each entry combines a (double)
value with a **Source**.

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

There are three types of StatisticJournal, for values that are integers,
floats and text.

### Sources

There are several different Sources:

* **Activities** are read from FIT files and provide a wealth of statistics
  (note that the GPS trace, HR time series, etc, are not stored as statistics
  themselves, but values calculated from these, like time in HR zones, total
  distance, are).

* **Topics** are used to structure entries in the diary and can be associated
  with statistics that are entered by the user (depending on the details of
  configuration).

* **Intervals** in time are used as sources for derived statistics.  This may
  seem somewhat abstract, but it helps avoid stale data (see below).  An
  Interval has a start time and a duration - typically a day, month or year.
  So the total distance cycled over May 2018, for example, is a derived
  statistic whose source is the interval covering that month.

As with Statistics and the StatisticJournal, the data associated with these
Activities and Topics are stored in **ActivityJournal** and **TopicJournal**
(the Activity and Topic tables store metadata).

Every Source has an associated time - this is also the time for the statistic.

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

Source has three children: Interval, ActivityJournal, and TopicJournal.

StatisticJournal also has three children: StatisticJournalInteger,
StatisticJournalFloat and StatisticJournalText.  StatisticJournal has a
foreign key relationship with Source, so that when a Source is deleted the
corresponding statistics are deleted (via cascade).

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

A Topic can be associated with various Statistics.  The associated
StatisticJournal entries can then be read and modified within the diary.

Configuration of this is necessarily quite complex, but a default
configuration is provided with Choochoo.

Example Topics include:

* Simple diary entries (mood, weather, sleep tracking).  In this case the
  schedule is daily with open range.

* Injuries and medication.  In this case the schedule will have the range of
  the injury and, for a particular medicine or treatment, might be on certain
  days.

* Training plans.  In this case the tree structure of Topics is used heavily
  and individual entries may be only a single day.
