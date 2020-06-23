
# Command Summary

* [help](#help)
* [web](#web)
* [read](#read)
* [search](#search)
* [constants](#constants)
* [validate](#validate)
* [jupyter](#jupyter)
* [kit](#kit)
* [database](#database)
* [import](#import)
* [garmin](#garmin)
* [calculate](#calculate)
* [fit](#fit)
* [fix-fit](#fix-fit)
* [thumbnail](#thumbnail)
* [package-fit-profile](#package-fit-profile)
* [show-schedule](#show-schedule)
* [unlock](#unlock)


## help

    > ch2 help [topic]

Displays help for a particular topic.

### Examples

    > ch2 help help

Displays this information.

    > ch2 help

Lists available topics.



## web

    > ch2 web start

Start the web server.

    > ch2 web status

Indicate whether the server is running or not.

    > ch2 web stop

Stop the server.



## read

    > ch2 read --kit ITEM [ITEM...] -- PATH [PATH ...]

Read FIT files, storing the data in the permanent store on the file system, 
then scan their contents, adding entries to the database, and finally 
calculating associated statistics. Both monitor and activity files are 
accepted.

Scanning and calculation of activities can be disabled with --disable, and 
individual steps can be enabled / disabled by name.

### Examples

    > ch2 read --kit cotic -- ~/fit/2018-01-01.fit

will store the given file, add activity data to the database (associated with 
the kit 'cotic'), check for new monitor data, and update statistics.

    > ch2 read --calculate

is equivalent to `ch2 calculate` (so will not store and files, will not read 
data, but wil calculate statistics).

    > ch2 read --disable --calculate [PATH ...]

will read files and add their contents to the database, but not calculate 
statistics.

    > ch2 read --disable [PATH ...]

will read files (ie copy them to the permanent store), but do no other 
processing.

Note: When using bash use `shopt -s globstar` to enable ** globbing.



## search

    > ch2 search text QUERY [--show NAME ...] [--set NAME=VALUE]
    > ch2 search activities QUERY [--show NAME ...] [--set NAME=VALUE]
    > ch2 search sources QUERY [--show NAME ...] [--set NAME=VALUE]

Search the database.

The first form (search text) searches for the given text in activity name and 
description.

The second form (search activities) is similar, but allows for more complex 
searches (similar to SQL) that target particular fields.

The third form (search sources) looks for matches for any source (not just 
activities).

Note that 'search activities' treats both activity journals and activity 
topics (ie data from FIT files and data entered by the user) as a single 
'source', while 'search activities' treats each source as separate.

Once a result is found additional statistics from that source be displayed 
(--show) and a single value modified (--set).

The search syntax (for activities and sources) is similar to SQL, but element 
names are statistic names. A name has the format "Owner.name:group" where the 
owner and group are optional. A trailing colon implies a NULL group (used for 
statistics that are not specific to any activity, like diary entries). The 
name and group also include SQL wildcards (eg "%fitness%").

The owner of a name is the process that calculated the value. It works as a 
kind of "namespace" - the database could contain multiple statistics called 
"active_distance" but only one will have been calculated by 
ActivityCalculator.

In addition, attributes of the source can be accessed using "Class.attribute" 
where Class is optional. For showing or setting values on the result, Class 
must be omitted (so .start=... sets the start attribute).

For complex searches, string values must be quoted, negation and NULL values 
are not supported, and comparison must be between a name and a value (not two 
names).

There is experimental support for null values (actually missing values). The 
form of the query is less general than SQL - a field must always be compared 
with a value (not another field).

### Examples

    > ch2 search text bournemouth

Find any activities where the text mentions Bournemouth.

    > ch2 search sources 'name="Wrong Name"' --set 'name="Right Name"'

Modify the name variable.

    > ch2 search activities 'ActivityCalculator.active_distance:mtb > 10 and active_time < 3600'

Find mtb activities that cover over 10km in under an hour.

    > ch2 search activities 'name="%"' --show .start name

Find activities that have a defined name and display both the name and the 
activity start time (the 'dot' syntax allows access to an attribute on the 
found activity).

    >  ch2 search activities 'ActivityJournal.start=2020-04-17T09:27:30' --set name='Corral Quemado'

Set the name on the activity at the given time (again, using the dot syntax).



## constants

    > ch2 constants list

Lists constant names on stdout.

    > ch2 constants show [NAME [DATE]]

Shows constant names, descriptions, and values (if NAME is given) on stdout.

    > ch2 constants add NAME

Defines a new constant.

    > ch2 constants set NAME VALUE [DATE]

Adds an entry for the constant. If date is omitted a single value is used for 
all time (so any previously defined values are deleted).

Note that adding / removing constants (ie their names) is separate from 
setting / deleting entries (ie their values).

    > ch2 constants unset NAME [DATE]

Deletes an entry.

    > ch2 constants remove NAME

Remove a constant (the associated entries must have been deleted first).

### Names

A constant name is a token (lower case letters, digits and underscores) 
optionally followed by a colon and the name of an activity group.

Names can be matched by SQL patterns. So FTHR.% matches both FTHR.Run and 
FTHR.Bike, for example. In such a case "entry" in the descriptions above may 
refer to multiple entries.



## validate

    > ch2 validate

This is still in development.



## jupyter

    > ch2 jupyter show ...

Show the template in the browser, starting a background Jupyter server if 
necessary.

    > ch2 jupyter list

List the available templates and their arguments.

    > ch2 jupyter status

Indicate whether the background server is running or not.

    > ch2 jupyter stop

Stop the background server.



## kit

Track equipment, including the lifetime of particular components.

    > ch2 kit new GROUP ITEM
    > ch2 kit change ITEM COMPONENT MODEL
    > ch2 kit statistics ITEM

For full details see `ch2 kit -h` and `ch2 kit SUBCOMMAND -h`.

### Examples

Note that in practice some commands that do 'important' changes to the 
database require `--force` for confirmation.

    > ch2 kit start bike cotic
    > ch2 kit change cotic chain sram --start
    # ... some months later ...
    > ch2 kit change cotic chain kmc
    # ... more time later ...
    > ch2 kit change cotic chain sram
    > ch2 kit statistics chain

This example will give statistics on how long (time, distance) different bikes 
chains lasted.

In addition, when importing activities, the `kit` variable must be defined. 
So, for example:

    > ch2 activities -D kit=cotic **/*.fit

In this way the system knows what equipment was used in what activity.

Finally, statistics may be incorrect if the equipment is modified (because the 
correct use will not be associated with each activity). To recalculate use

    > ch2 kit rebuild

For running shoes you might simply track each item:

    > ch2 kit start shoe adidas
    # ... later ...
    > ch2 kit finish adidas
    > ch2 kit start shoe nike

Statistics for shoes:

    > ch2 kit statistic shoe

Names can be chosen at will (there is nothing hard-coded about 'bike', 
'chain', 'cotic', etc), but in general must be unique. They can contain spaces 
if quoted.



## database

    > ch2 database load (--sqlite|--pgsql|--uri URI) [--delete] PROFILE

Load the initial database schema.

    > ch2 database list

List the available profiles.

    > ch2 database show

Show the current database state.

    > ch2 database delete

Delete the current database.



## import

    > ch2 import 0-30

Import data from a previous version (after starting a new version). Data must 
be imported before any other changes are made to the database.

By default all types of data (diary, activities, kit, constants and segments) 
are imported. Additional flags can enable or disable specific data types.

### Examples

    > ch2 import --diary 0-30

Import only diary entries.

    > ch2 import --disable --diary 0-30

Import everything but diary entries.



## garmin

    > ch2 garmin --user USER --pass PASSWORD DIR

Download recent monitor data to the given directory.

    > ch2 garmin --user USER --pass PASSWORD --date DATE DIR

Download monitor data for the given date.

Note that this cannot be used to download more than 10 days of data. For bulk 
downloads use https://www.garmin.com/en-US/account/datamanagement/



## calculate

    > ch2 calculate

Calculate any missing statistics.

    > ch2 calculate --force [START [FINISH]]

Delete statistics in the date range (or all, if omitted) and then calculate 
new values.

    > ch2 --dev calculate --like '%Activity%' --force 2020-01-01 -Kn_cpu=1

Calculate activity statistics from 2020 onwards in a single process for 
debugging.



## fit

    > ch2 fit SUB-COMMAND PATH [PATH ...]

Print the contents of fit files.

The format and details displayed are selected by the sub-command: records, 
tables, messages, fields, csv and grep (the last requiring patterns to match 
against).

For a list of sub-commands options see `ch2 fit -h`.

For options for a particular sub-command see `ch2 fit sub-command -h`.

Note: When using bash use `shopt -s globstar` to enable ** globbing.

### Examples

    > ch2 -v 0 fit records ride.fit

Will print the contents of the file to stdout (use `-v 0` to suppress logging 
or redirect stderr elsewhere).

    > ch2 -v 0 fit grep -p '.*:sport=cycling' --match 0 --name directory/**/*.fit

Will list file names that contain cycling data.

    > ch2 fit grep -p PATTERN -- FILE

You may need a `--` between patterns and file paths so that the argument 
parser can decide where patterns finish and paths start.



## fix-fit

    > ch2 fix-fit PATH -o PATH --drop

Try to fix a corrupted fit file.

If `--header` is specified then a new header is prepended at the start of the 
data.

If `--slices` is specified then the given slices are taken from the data and 
used to construct a new file.

If `--drop` is specified then the program tries to find appropriate slices by 
discarding data until all the remaining data can be parsed.

If `--fix-header` is specified then the header is corercted.

If `--fix-checksum` is specified then the checksum is corrected.

### Examples

    > ch2 fix-fit FILE.FIT --slices 1000: --fix-header --fix-checksum

Will attempt to drop the first 1000 bytes from the given file.

    > ch2 fix-fit data/tests/personal/8CS90646.FIT --drop --fix-header --fix-checksum

Will attempt to fix the given file (in the test data from git).

    > ch2 fix-fit FILE.FIT --add-header --header-size 14 --slices :14,28: --fix-header --fix-checksum

Will prepend a new 14 byte header, drop the old 14 byte header, and fix the 
header and checksum values.



## thumbnail

    > ch2 thumbnail ACTIVITY-ID
    > ch2 thumbnail DATE

Generate a thumbnail map of the activity route.



## package-fit-profile

    > ch2 package-fit-profile data/sdk/Profile.xlsx

Parse the global profile and save the structures containing types and messages 
to a pickle file that is distributed with this package.

This command is intended for internal use only.



## show-schedule

    > ch2 show-schedule SCHEDULE

Print a calendar showing how the given schedule is interpreted.

### Example

    > ch2 show-schedule 2w[1mon,2sun]

(Try it and see)



## unlock

    > ch2 unlock

Remove the "dummy" entry from the SQLite database that is used to coordinate 
locking across processes.

This should not be needed in normal use. DO NOT use when worker processes are 
still running. Has no effect when used with PostgreSQL.

