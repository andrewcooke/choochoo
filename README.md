
# choochoo (ch2)

An **open**, **hackable** and **free** training diary.

* Training data are stored in a database
  * There are tools to get data into the database:
    * Read FIT files from smart watches, bike computers, etc
    * Daily information (eg weight) can be entered via the diary
      * Ability to add custom fields for general data capture
      * Dedicated tracking of injuries
    * Other data (eg FTHR) can be entered at the command line
  * There are tools to process data in the database:
    * Prepared calculations for data totals, ranking
    * Calculation of TSS
    * Ability to extend processing with Python
  * There are tools to get data out of the database:
    * Pandas tables for analysis in numpy
    * Support for Jupyter notebooks
    * Prepared plotting routines for common operations (eg ???)
    * Daily, monthly and yearly textual summaries
  * Clear database schema, designed for third party access
    * SQLAlchemy ORM interface
* Ability to schedule diary reminders for regular events
  * This is used to schedule training plans
    * Prepared / example training plans included
    * Simple, declarative library for defining your own plans
* System configuration via Python prompt

Can be used stand-alone or could be extended with a GUI.
See [documentation](https://andrewcooke.github.io/choochoo/).

**This branch under development - not all the above implemented.**
