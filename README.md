
# choochoo (ch2)

An **open**, **hackable** and **free** training diary.

Training data are stored in a database...

* There are tools to get data into the database:
  * Read FIT files from smart watches, bike computers, etc
  * Daily information (eg weight) can be entered via the diary
    * Ability to add custom fields for general data capture
    * Dedicated tracking of injuries
  * Other data (eg FTHR) can be entered at the command line
* There are tools to process data in the database:
  * Prepared calculations for data totals, ranking
  * Ability to extend processing with Python
* There are tools to get data out of the database:
  * Pandas tables for analysis in numpy and Jupyter notebooks
  * Examples for plotting spatial and time-series data
* Clear database schema, designed for third party access
  * SQLAlchemy ORM interface

The configuration is also stored in the database...

* You can schedule training plans
  * Prepared / example training plans included
  * Simple, declarative library for defining your own plans
* You can add data fields to the diary
* You can extend the statistics calculation pipeline

The project can be used stand-alone by someone comfortable with the
technologies used, or it could be extended with a GUI.  See
[documentation](https://andrewcooke.github.io/choochoo/) for more
details.

## Latest Changes

### v0.2.0

Major rewrite to generalize the database schema.  Moved a lot of
configuration into the database.  Now much more flexible, but less
interactive.
