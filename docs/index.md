
An **open**, **hackable** and **free** training diary.

The main interface is a curses-style diary, used to track daily
activity as well as progress towards aims.  Entries in the diary
("topics") are configured by the user, can be associated with values
in the database ("statistics"), and can include "schedules" to define
periodic events (eg training routines).

Data can be imported from FIT files (from smart watches and bike
computers) and summary statistics generated for configurable periods
(eg per month or per year).  All data are stored in an sqlite3
database.  For plotting and analysis they can be exported to pandas
data frames in a Jupyter notebook.

Above all, the system is *open and extensible*.  You can define your
own training plans.  You can add calculations (eg training stress
score).  You can hack the code.  The code is structured so that you
can re-use the parts you need (ORM for database?  library to read FIT
files?  it's all available).

One omission that may be important to some people is the lack of
emphasis on power meters.

* [Install](install) - installing Choochoo.
* [Configure](configure) - configuring the system.
* [The Diary](diary) - entering daily data.
* [Activities](activities) - import and organise activity data.
* [Scheduling](scheduling) - defining regular events.
* [Training Plans](training-plans) - in-built and custom plans.
* [Analysis](analysis) - explore data in Jupyter notebooks. 
* [FIT Files](fit-files) - display FIT format data.

## Current Status

The framework is there: a database; various ways of getting data into
the database; various ways of getting it out again.  Unfortunately I
am injured and recently had a set-back in my recovery, so the actual
training part isn't so detailed.

## Future Plans

The system was recently re-written to be more configurable and
general.  Next steps include:

* Updating this documentation.
  * Add docs for "quantified self" users, since they may also be
    interested.
  * Add screenshots and examples.
* Adding a TSS equivalent using heart rate values.
