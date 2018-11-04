
# Introduction

Choochoo helps you plan, collect, process and analyse training data.

Data can be entered by hand, in the "diary", or read from FIT files.
It includes support for downloading FIT files from Garmin Connect.

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

Further "derived" data can be calculated from the raw data you
provide.  A simple example would be rankings (eg per month).  A more
complex example (not yet implemented) would be Training Stress Score
(TSS).

If you develop your own calculations (as Python code) then these can
be added to the "pipeline" and run automatically on new data.

All these data are stored in an SQLite database, in a single file.
This is easy to copy to safe storage and allows you to read and
process the data with your own programs.

The data can also be extracted as Panda DataFrames.  Typically this is
done in the Jupyter environment, where you can interactively analyse
and plot the information.

One omission that may be important to some people is the lack of
support for power meters.

# Contents

* [Install](install) - installing Choochoo.
* [Configure](configure) - configuring the system.
* [The Diary](diary) - entering daily data.
* [Activities](activities) - import and organise activity data.
* [Scheduling](scheduling) - defining regular events.
* [Training Plans](training-plans) - in-built and custom plans.
* [Analysis](analysis) - explore data in Jupyter notebooks. 
* [FIT Files](fit-files) - display FIT format data.

