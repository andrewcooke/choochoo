
# Command Summary

* [help](#help)
* [web](#web)
* [upload](#upload)
* [diary](#diary)
* [constants](#constants)
* [jupyter](#jupyter)
* [kit](#kit)
* [configure](#configure)
* [upgrade](#upgrade)
* [activities](#activities)
* [garmin](#garmin)
* [monitor](#monitor)
* [statistics](#statistics)
* [dump](#dump)
* [fit](#fit)
* [fix-fit](#fix-fit)
* [no-op](#no-op)
* [package-fit-profile](#package-fit-profile)
* [test-schedule](#test-schedule)
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



## upload

    > ch2 upload --kit ITEM [ITEM...] -- PATH [PATH ...]

Upload FIT files, storing the data in the permanent store (Data.Dir) on file 
system. Optionally (if not --fast), scan the files and appropriate entries to 
the database. Both monitor and activity files are accepted.

Files are checked for duplication on uploading (before being scanned).

If the uploaded file is mapped to a file path that already exists then we 
check the following cases:
* If the hash matches then the new data are discarded (duplicate).
* If the hash is different, it is an error (to avoid losing activity diary entries which are keyed by hash).

If the uploaded file has a hash that matches a file already read into the 
database, but the file path does not match, then it is an error (internal 
error with inconsistent naming or duplicate data).

If --unsafe is given then files whose hashes match existing files are simply 
ignored. This allows data downloaded en massed from Garmin to be uploaded 
ignoring already-uploaded data (with kit).

In short, hashes should map 1-to-1 to file names and to activities, and it is 
an error if they do not.

### Examples

    > ch2 upload --kit cotic -- ~/fit/2018-01-01.fit

will store the given file, add activity data to the database (associated with 
the kit 'cotic'), check for new monitor data, and update statistics.

Note: When using bash use `shopt -s globstar` to enable ** globbing.



## diary

    > ch2 diary [DATE]

The date can be an absolute day or the number of days previous. So `ch2 diary 
1` selects yesterday.

Display the daily diary. Enter information here.

To exit, alt-q (or, without saving, alt-x).

    > ch2 diary (--month | --year | --schedule SCHEDULE) [DATE}

Display a summary for the month / year / schedule.



## constants

    > ch2 constants show [NAME [DATE]]

Lists constants to stdout.

    > ch2 constants add NAME

Defines a new constant.

    > ch2 constants set NAME VALUE [DATE]

Adds an entry for the constant. If date is omitted a single value is used for 
all time (so any previously defined values are deleted).

Note that adding / removing constants (ie their names) is separate from 
setting / deleting entries (ie their values).

    > ch2 constants delete NAME [DATE]

Deletes an entry.

    > ch2 constants remove NAME

Remove a constant (the associated entries must have been deleted first).

Names can be matched by SQL patterns. So FTHR.% matches both FTHR.Run and 
FTHR.Bike, for example. In such a case "entry" in the descriptions above may 
refer to multiple entries.

TODO - Constraint handling is confused and confusing.



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



## configure

    > ch2 configure load default

Generate a simple initial configuration.

Please see the documentation at http://andrewcooke.github.io/choochoo - you 
have a lot more options!

    > ch2 configure check --no-config --no-data

Check that the current database is empty.



## import

    > ch2 import 0-30

Import diary entries from a previous version.



## activities

    > ch2 activities [--kit ITEM [ITEM ...] --] [PATH [PATH ...]]

Read activities data from FIT files.

### Examples

    > ch2 activities -D kit=cotic ~/fit/2018-01-01.fit

will load the given file and associated the activity with the kit 'cotic'.

    > ch2 activities --kit

will load all unread files from the standard location (constant Data.Dir, 
where they are stored by the upload command) reading the kit from the file 
name (as encoded by the upload command).

Note: When using bash use `shopt -s globstar` to enable ** globbing.



## garmin

    > ch2 garmin --user USER --pass PASSWORD DIR

Download recent monitor data to the given directory.

    > ch2 garmin --user USER --pass PASSWORD --date DATE DIR

Download monitor data for the given date.

Note that this cannot be used to download more than 10 days of data. For bulk 
downloads use https://www.garmin.com/en-US/account/datamanagement/



## monitor

    > ch2 monitor PATH [PATH ...]

Read monitor data from FIT files.

Note: When using bash use `shopt -s globstar` to enable ** globbing.



## statistics

    > ch2 statistics

Generate any missing statistics.

    > ch2 statistics --force [DATE]

Delete statistics after the date (or all, if omitted) and then generate new 
values.



## dump

    > ch2 dump COMMAND

Simple access to the database - similar to the interface provided in Jupyter 
notebooks, but accessed from the command line.

The format can be selected with `--print` (the default), `--csv` and 
`--describe`.

For full options see `ch2 data -h` and `ch2 data COMMAND -h`

### Examples

    > ch2 dump --csv table StatisticName

Will print the contents of the StatisticName table in CSV format.

    > ch2 dump statistics '%HR%' --constraint 'ActivityGroup "Bike"' --start 2018-01-01

Will print HR-related statistics from the start of 2018 for the given activity 
group.



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



## no-op

This is used internally when accessing data in Jupyter or configuring the 
system at the command line.



## package-fit-profile

    > ch2 package-fit-profile data/sdk/Profile.xlsx

Parse the global profile and save the structures containing types and messages 
to a pickle file that is distributed with this package.

This command is intended for internal use only.



## test-schedule

    > ch2 test-schedule SCHEDULE

Print a calendar showing how the given schedule is interpreted.

### Example

    > ch2 test-schedule 2w[1mon,2sun]

(Try it and see)



## unlock

    > ch2 unlock

Remove the "dummy" entry from the database that is used to coordinate locking 
across processes.

This should not be needed in normal use. DO NOT use when worker processes are 
still running.

