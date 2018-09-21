
An **open**, **hackable** and **free** training diary.

The main interface is a curses-style diary, used to track daily activity
as well as progress towards aims.  A flexible "schedule spec" is used to
define periodic events (eg training routines) and (unfortunately) there's 
dedicated functionality for tracking injuries.

Data can be imported from FIT files (from smart watches and bike computers)
and summary statistics generated monthly or annually.  All data are stored
in an sqlite3 relation database.  For plotting and analysis they can be 
exported to pandas data frames in a Jupyter notebook.

Above all, the system is *open and extensible*.  You can define your own 
training plans.  You can hack the code.  The code is structured so that you
can re-use the parts you need (ORM for database?  library to read FIT files?
it's all available).  

One omission that may be important to some people is the (purposeful)
lack of emphasis on power meters.

* [Install](install) - installing Choochoo.
* [The Diary](diary) - entering daily data.
* [Activities](activities) - import and organise activity data.
* [Scheduling](scheduling) - defining regular events.
* [Training Plans](training-plans) - in-built and custom plans.
* [Analysis](analysis) - explore data in Jupyter notebooks. 
* [FIT Files](fit-files) - display FIT format data.

## Current Status

The framework is there.  A database.  Various ways of getting data into
the database.  Various ways of getting it out again.  Unfortunately I am
injured and recently had a set-back in my recovery, so the actual 
training part isn't so detailed.

## Future Plans

Motivated by an initial announcement of this code on Reddit, which helped
me clarify to myself what I was trying to do here:

* Rewrite the database so that numerical values are isolated in a single
  table (and the ORM to use factories that look-up values there).
* Make calculation of summary statistics more general, working on the
  single table of values.
* Allow summary statistics over multiple ranges.
* Support pluggable / extensible statistics.
* Remove the complexity of configuration TUIs by moving configuration
  to something done at the Python (or Jupyter) prompt (like analysis).
* Rewrite the diary display so that it can handle arbitrary fields
  (and the binder). 
* Document all the above in the spirit of "you can extend it" and
  "move data in and out of database".
