
Choochoo helps you plan, collect, process and analyse training data.

Data are combined from three sources:

  * [FIT files](fit-files), both for activities and monitoring (ie
    steps, heart rate).  The latter can be downloaded from Garmin.

  * Text entry via a '[diary](daily-use)' that runs in the terminal.

  * Direct commands (eg [tracking equipment changes](kit)).

Data are combined in an SQLite database that can be accessed via SQL
or as Panda data frames.  This is easy to copy to safe storage and
allows you to read and process the data within your own programs.

The data can be processed via 'pipelines'.  Existing calculations
include [power estimation](cda), [fitness/fatigue](impulse) and
summary values (eg ranking, top value per month).  If you develop your
own calculations (as Python code) then these can be added as a
'pipeline' and run automatically on new data.

Display and analysis of data via [Jupyter](data-analysis) is
supported, with an embedded Jupyter server and pre-written templates
for common operations (eg [displaying data for an activity](summary),
displaying [similar routes](nearby)).

The diary configuration (ie what fields are displayed) is very
flexible and can be used to present [training plans](training-plans).
Indeed, the whole system (diary fields, pipelines, activiy groups,
equipment tracking, etc) can be configured via the database.  A
[default configuration](configuration) is provided, but this can be
modified or replaced.

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
  * [Version Upgrades](version-upgrades)
  * [Reading FIT Files](fit-files)
  * [Repairing FIT Files](fix-fit)
  * [FIT Cookbook](fit-cookbook)
  * [Training Plans](training-plans)
  * [Scaled Heart Rate Impulse - SHRIMP](impulse)
  * [Segments](segments)
  * [Nearby Activities](nearby)
  * [Graphic Summary](summary)
  * [Elevation](elevation)
  * [Detecting Climbs](climbs)
  * [Measuring Power and CdA](cda)
  * [Tracking Equipment](kit)
* Development
  * [Spatial Search](rtree)
  * [Other Projects](other-projects)
