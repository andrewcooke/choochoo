
# FIT Cookbook

* [Installing Choocoo](#installing-choochoo)
* [Check a FIT File](#check-a-fit-file)
* [Check Many FIT Files](#check-many-fit-files)
* [Check Timestamps in a FIT File](#check-timestamps-in-a-fit-file)
* [Remove a Bad Timestamp from a FIT File](#remove-a-bad-timestamp-from-a-fit-file)
* [See What Data are Dropped](#see-what-data-are-dropped)
* [See What Data are Dropped in Detail](#see-what-data-are-dropped-in-detail)
* [Remove Arbitrary Data from a FIT File](#remove-arbitrary-data-from-a-fit-file)
* [Change the Times in a FIT File](#change-the-times-in-a-fit-file)
* [Search for Values in a FIT File](#search-for-values-in-a-fit-file)
* [Search for Values in a FIT File with Context](#search-for-values-in-a-fit-file-with-context)
* [Find FIT Files with Values](#find-fit-files-with-values)
* [Restrict Displayed Dates](#restrict-displayed-dates)
* [Read a FIT File in Python](#read-a-fit-file-in-python)

## Installing Choocoo

Instructions for install are [here](getting-started).

If you only want to use the python library programatically there is no
need to configure the system.

If you only want to use the `ch2 fit` and `ch2 fix-fit` commands, the
default configuration (`ch2 default-config`) is sufficient.

## Check a FIT File

To check for errors in `myfile.fit`:

    > ch2 fix-fit myfile.fit --discard
        INFO: Version 0.24.5
        INFO: Using database at ...
        INFO: Input ----------
        INFO: Reading binary data from myfile.fit
        INFO: Initial Data ----------
        INFO: Length: 5368 bytes
        INFO: Header size: 14
        INFO: Protocol version: 16
        INFO: Profile version: 2014
        INFO: Checksum: 37636 (0x9304)
        INFO: Validation ----------
        INFO: --max-delta-t None
     WARNING: Time-reversal is allowed unless max-delta-t is set
        INFO: First timestamp: 2018-07-26 13:34:49+00:00
        INFO: Last timestamp:  2018-07-26 13:59:18+00:00
        INFO: OK
        INFO: Final Data ----------
        INFO: Length: 5368 bytes
        INFO: Header size: 14
        INFO: Protocol version: 16
        INFO: Profile version: 2014
        INFO: Checksum: 37636 (0x9304)
        INFO: Output ----------
        INFO: Discarded output


If there are no warnings or errors (as above) then the file is OK (as
far as my code can tell - to check timestamps see the next recipe).

## Check Many FIT Files

Maybe we have a collection of files and we want to know which have
problems.  Note that using `-v 2` reduces the logging to `ERROR` level
only (with `-v 0` we would see no logging, just the file names).

