
# Command Summary

* [activities](#activities)
* [constants](#constants)
* [data](#data)
* [default-config](#default-config)
* [diary](#diary)
* [fit](#fit)
* [fix-fit](#fix-fit)
* [garmin](#garmin)
* [help](#help)
* [monitor](#monitor)
* [statistics](#statistics)
* [no-op](#no-op)
* [package-fit-profile](#package-fit-profile)
* [test-schedule](#test-schedule)
* [unlock](#unlock)


## activities

    > ch2 activities PATH [PATH ...]

Read activities data from FIT files.

### Examples

    > ch2 activities -D 'Bike=Cotic Soul' ~/fit/2018-01-01.fit

will load the give file and create an entry for the `Bike` statistic with
value `Cotic Soul` (this particular variable is used to identify bike-specific
parameters for power calculation, but arbitrary names and values can be used).

Note: When using bash use `shopt -s globstar` to enable ** globbing.    



## constants

    > ch2 constants [NAME [DATE]]

Lists constants to stdout.

    > ch2 constants --set NAME [DATE] VALUE

Defines a new entry.  If date is omitted a single value is used for all time
(so any previously defined values are deleted)

    > ch2 constants --delete NAME [DATE]

Deletes an entry.

Names can be matched by SQL patterns.  So FTHR.% matches both FTHR.Run and
FTHR.Bike, for example. In such a case "entry" in the descriptions above may
refer to multiple entries.    



## data

    > ch2 data COMMAND

Simple access to the database - similar to the interface provided in
JupyterState notebooks, but accessed from the command line.

The format can be selected with `--print` (the default), `--csv` and
`--describe`.

For full options see `ch2 data -h` and `ch2 data COMMAND -h`

### Examples

    > ch2 data --csv table StatisticName

Will print the contents of the StatisticName table in CSV format.

    > ch2 data statistics '%HR%' --constraint 'ActivityGroup "Bike"' --start
    2018-01-01

Will print HR-related statistics from the start of 2018 for the given activity
group.    



## default-config

    > ch2 default-config

Generate a simple initial configuration.

Please see the documentation at http://andrewcooke.github.io/choochoo    



## diary

    > ch2 diary [DATE]

The date can be an absolute day or the number of days previous.  So `ch2 diary
1` selects yesterday.

Display the daily diary.  Enter information here.

To exit, alt-q (or, without saving, alt-x).

    > ch2 diary (--month | --year | --schedule SCHEDULE) [DATE}

Display a summary for the month / year / schedule.    



## fit

    > ch2 fit PATH [PATH ...]

Print the contents of fit files.

The format and details displayed can be selected with --records, --tables,
--grep, --messages, --fields, and --csv.

For full options see `ch2 fit -h`.

Note: When using bash use `shopt -s globstar` to enable ** globbing.

### Examples

    > ch2 -v 0 fit --records ride.fit

Will print the contents of the file to stdout (use `-v 0` to suppress logging
or redirect stderr elsewhere).

    > ch2 -v 0 fit --grep '.*:sport=cycling' --match 0 --name
    directory/**/*.fit

Will list file names that contain cycling data.

    > ch2 fit --grep PATTERN -- FILE

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

    > ch2 fix-fit data/tests/personal/8CS90646.FIT --drop --fix-header
    --fix-checksum

Will attempt to fix the given file (in the test data from git).

    > ch2 fix-fit FILE.FIT --add-header --header-size 14 --slices :14,28:
    --fix-header --fix-checksum

Will prepend a new 14 byte header, drop the old 14 byte header, and fix the
header and checksum values.    



## garmin

    > ch2 garmin --user USER --pass PASSWORD DIR

Download recent monitor data to the given directory.

    > ch2 garmin --user USER --pass PASSWORD --date DATE DIR

Download monitor data for the given date.

Note that this cannot be used to download more than 10 days of data. For bulk
downloads use https://www.garmin.com/en-US/account/datamanagement/    



## help

    > ch2 help [topic]

Displays help for a particular topic.

### Examples

    > ch2 help help

Displays this information.

    > ch2 help

Lists available topics.    



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



## no-op

This is used internally when accessing data in JupyterState or configuring the
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

    > ch2 unlock --force

Remove any locking.

The database is locked to allow fast loading of data which requires no other
command access the database. Using this command removes the lock and so MAY
CAUSE DATA CORRUPTION if the loading is still in progress.

You should only use this command in the unlikely case that somehow the lock
remained after the loading finished (eg. if the system crashed or was
interrupted during loading).    

