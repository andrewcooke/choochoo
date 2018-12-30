
# Repairing FIT Files

Choochoo includes a tool that will attempt to repair FIT format files.
It does this by trying to *discard* data until it finds a valid file
(this works because a FIT file is mainly a sequence of repeated
records, one for each GPS point; if we remove a corrupt record we
still have nearly all the data).

## For Dummies

The FIT format is complex so it is difficult to make a simple,
automatic tool, but if you do not want to read this documentation the
following might work:

    > ch2 fix-fit INPUT.FIT --add-header --drop --max-drop-cnt 2 -o OUTPUT.FIT

To run that you first need to [install Choochoo](getting-started).

## Overview

The program runs in a series of steps:

  * If `--add-header` is given, a blank file header is prepended to
    the start of the data.  See [Add Header](#add-header).

  * If `--drop` is given, a search is made to find (a fairly minimal
    amount of) data that can be discarded so that the file can be
    parsed.  The data are not actually modified at this point -
    instead, a list of data slices to be kept is constructed.  See
    [Drop Data](#drop-data).

  * The data are sliced.  This will normally use the slices found
    above, but slices can also be specified at the command line with
    `--slices`.  See [Slices](#slices).

  * The file header and final checksum are modified to reflect the new
    data.  See [Header and Checksums](#header-and-checksums).

  * The data are validated.  See [Validation](#validation).

  * The results are written to a file, stdout, or discarded.  See
    [Output](#output).

Modifications made to the data should be logged at the "warning" level
in the logs.

### Not Quite So Dummy

Given the above we can unpack

    > ch2 fix-fit INPUT.FIT --add-header --drop --max-drop-cnt 2 -o OUTPUT.FIT

The `--add-header` means that a new header is added to the beginning
of the data.  Since the data may already contain a header this will
introduce a parsing error (unless you are very unlucky and the old
header looks like valid data).  Using `--drop` will hopefully then
discard the old header.

The likely result of the recipe above, then, is to replace the old
header with a new one.  If we had *not* used `--add-header` the old
header would have been "fixed" (see [Header and
Checksums](#header-and-checksums)), but that would not have corrected
any issues if a byte (or more) of data was actually *missing* from the
header (since fixing assumes that the data have the correct length).

If the original header was OK, we did a bunch of work for no reason
and the problem is elsewhere in the file.  This is why `--max-drop-cnt
2` is given - it allows `--drop` to drop a *further* region of data
(making two drops in total) and hopefully fix the issue.

So in total, the recipe allows for two fixes: one to the header and
another somewhere in the data.

Finally the file length and checksums are fixed and the data saved to
`OUTPUT.FIT`.

## Add Header

The `--header-size`, `--protocol-version` and `--profile-version`
flags can be used to fine-tune the header.  Default values are taken
from FR35 FIT files.  To see the defaults run the program without
specifying the option and read the logs (`--discard` is useful here -
see [Output](#output)).

Note that adding the header increases the data size.  So if used with
`--slices` you must take this into account (and add `--header-size` to
your indices).

For example, the following command tests replacing an existing 14 byte
header:

    > ch2 fix-fit INPUT.FIT --add-header --header-size 14 --slices :14,28: --discard

## Drop Data

This is the heart of the algorithm.  A depth first search is made to
find discards that allow the remaining data to be parsed.  The details
of this search can be inferred from the parameters below, but if you
really, really want the details you will need to read the
[source](https://github.com/andrewcooke/choochoo/blob/master/ch2/fit/fix.py).

The following parameters influence the search:

  * `--no-force` - if given, then the "inner details" of each record
    are not parsed.  This may be useful when the library cannot parse
    valid records, but it means that the search is less likely to
    detect corrupt data.  Default is to parse all data.

    If you need this flag, please raise a bug report so I can fix the
    underlying issue.

  * `--min-sync-cnt` - this is the number of records that must be read
    after some data are dropped for the modification to be considered
    "successful".  If this many records cannot be read (and sufficient
    data are available) then additional data will be discarded.
    Default 3.

  * `--max-record-len` - if given, records longer than this length are
    taken to indicate corrupt data.  Default unused.

  * `--max-drop-cnt` - the maximum number of regions of data that may
    be dropped.  Default 1.

  * `--max-back-cnt` - when searching for data to drop, the algorithm
    first advances through "good" data.  When it encounters "bad" data
    it may need to retreat and discard some records it had previously
    considered "good".  This is the maximum number of "good" records
    that can be discarded.  Default 3.

  * `--max-fwd-len` - the maximum number of bytes that can be
    discarded.  Default 200.
    
The slices determined by the search are printed to the log like this:

    INFO: Dropped data to find slices: :28020,28043:97437

## Slices

The slices are a comma-separated list of `lo:hi` pairs, where either
limit can be omitted.  The syntax is intended to match the Python
array syntax, so if the data are in the array `data`, then `lo:hi`
identifies the data `data[lo:hi]`.

The existing checksum should *not* be included in the slices.  To help
with this a final, open slice has the "stop" value replaced with `-2`.
So `:` (all data) would be changed to `:-2` (all data but the last two
bytes - the checksum).

Most slices will result in data that cannot be parsed, and so will
fail validation (see [Validation](#validation)).  This is why it is
best to use the slices found by `--drop` (see [Drop
Data](#drop-data)).

## Header and Checksums

Once data have been modified the file header and checksum are updated
appropriately.  If necessary, new values for `--protocol-version` and
`--profile-version` can be specified on the command line.

## Validation

The corrected data are parsed once more to validate that the changes
are correct.  This can be skipped with `--no-validate`.

## Output

By default, the results are printed to stdout in "hex" format (or raw
binary if `--raw` is given).  They can be saved to a file (in raw
binary format) using `-o` or `--output`.  Alternatively, the output
can be discarded using `--discard` (this is useful when fine-tuning
parameters).

## Further Reading

  * `ch2 fix-fit -h` and `ch2 help fix-fit` show options and use.

  * [The FIT library](fit-files) used by Choochoo.  This can be used
    to examine the contents of (valid) FIT files.

  * [The FIT SDK](https://www.thisisant.com/resources/fit/) includes
    documentation from Garmin.
    