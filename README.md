
# choochoo (ch2)

An **open**, **hackable** and **free** training diary.

See [documentation](https://andrewcooke.github.io/choochoo/) for full
details.

## Diary

![](docs/diary2.png)

## Jupyter

![](docs/statistics.png)

## Technical Features

Training data are stored in a database...

* There are tools to get data into the database:
  * Read FIT files from smart watches, bike computers, etc
    * 'Activities' (eg bike rides) can be read
    * 'Monitor' data (eg steps and rest HR) can be read
      * These can also be downloaded from Garmin Connect
  * Daily information (eg weight) can be entered via the diary
    * Ability to add custom fields for general data capture
  * Other data (eg FTHR) can be entered at the command line
* There are tools to process data in the database:
  * Prepared calculations for data totals, ranking, averages
  * Ability to extend processing with Python
* There are tools to get data out of the database:
  * Browse and edit data in the diary
  * Pandas tables for analysis in numpy and Jupyter notebooks
  * Examples for plotting spatial and time-series data
* Clear database schema, designed for third party access:
  * SQLAlchemy ORM interface

The configuration is also stored in the database...

* You can schedule training plans:
  * Prepared / example training plans included
  * Simple, declarative library for defining your own plans
* You can add data fields to the diary
* You can extend various pipelines that are called during processing:
  * Statistic pipeline to calculate new derived statistics
    (eg values over intervals)
  * Diary pipeline to generate items for diplsay in the diary
  * Activity pipeline to generate new data based on activities
  * Monitor pipeline to generate new data based on monitor data

The project can be used stand-alone by someone comfortable with the
technologies used, or it could be extended with a GUI.

## Latest Changes

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
