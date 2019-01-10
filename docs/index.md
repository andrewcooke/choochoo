
Choochoo helps you plan, collect, process and analyse training data.

Data can be entered by hand, in the "diary", or read from [FIT
files](fit-files).  Downloading FIT files from Garmin Connect is
supported.

The choice of what data to track is up to you.  A default
configuration is provided, but this can be modified.  You can add and
remove fields, and place them in an appropriate hierachy.  For
example, you could create a new set of fields to track a particular
injury (eg notes, pain, medication).

The data displayed in the diary can also be restricted to a range of
dates, or to repeat on certain days.  This means that it can be used
to display information about training plans.  It is relatively simple
to automate the creation of these entries (in Python) - examples are
provided.  In this way you can programaticaly generate training
schedules.

"Derived" data can be calculated from the raw data you provide.  A
simple example would be rankings (eg per month).  A more complex
example would be [Fitness / Fatigue models](impulse).

If you develop your own calculations (as Python code) then these can
be added to the "pipeline" and run automatically on new data.

All your data (raw and derived) are stored in an SQLite database, in a
single file.  This is easy to copy to safe storage and allows you to
read and process the data with your own programs.

The data can also be extracted as Panda DataFrames.  Typically this is
done in the [Jupyter](data-analysis) environment, where you can
interactively analyse and plot the information.

One omission that may be important to some people is the lack of
support for power meters.

# Contents

* Manual
  * [Getting Started](getting-started)
  * [Daily Use](daily-use)
  * [Data Analysis](data-analysis)
  * [Command Summmary](command-summary)
* Reference
  * [Data Model](data-model)
  * [Schedules](schedules)
  * [Configuration](configuration)
  * [Reading FIT Files](fit-files)
  * [Repairing FIT Files](fix-fit)
  * [FIT Cookbook](fit-cookbook)
  * [Training Plans](training-plans)
  * [Scaled Heart Rate Impulse - SHRIMP](impulse)
  * [Segments](segments)
  * [Nearby Activities](nearby)
  * [Graphic Summary](summary)
* Development
  * [Spatial Search](rtree)
  