
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
        INFO: Logging to /home/andrew/.ch2/0-35/logs/fix-fit.log
     WARNING: Could not connect to database
    
     Welcome to Choochoo.
    
     You must configure the database before use (no uri).
    
     Please use the ch2 database command.
    


If there are no warnings or errors (as above) then the file is OK (as
far as my code can tell - to check timestamps see the next recipe).

## Check Many FIT Files

Maybe we have a collection of files and we want to know which have
problems.  Note that using `-v 2` reduces the logging to `ERROR` level
only (with `-v 0` we would see no logging, just the file names).

    > ch2 -v 2 fix-fit --name-bad *.fit
    
     Welcome to Choochoo.
    
     You must configure the database before use (no uri).
    
     Please use the ch2 database command.
    


## Check Timestamps in a FIT File

To check that the timestamp never increases by more than 60s between
records:

    > ch2 fix-fit myfile.fit --max-delta-t 60 --discard
        INFO: Logging to /home/andrew/.ch2/0-35/logs/fix-fit.log
     WARNING: Could not connect to database
    
     Welcome to Choochoo.
    
     You must configure the database before use (no uri).
    
     Please use the ch2 database command.
    


Here we can see that there was a jump of 273 seconds.

## Remove a Bad Timestamp from a FIT File

The `fix-fit` command can "drop" data that cause errors.  In this case
(compare timestamps in the two recipes above) it is the final
timestamp that apperas to be wrong.  So we can drop that without
worrying about further, incorrect timestamps.

Note that dropping a record may remove important information from the
file (see below to understand what information is removed).

The command to drop data is (see notes below):

    > ch2 fix-fit myfile.fit --max-delta-t 60 --drop --fix-header --fix-checksum --max-fwd-len 500 -o fixed.fit
        INFO: Logging to /home/andrew/.ch2/0-35/logs/fix-fit.log
     WARNING: Could not connect to database
    
     Welcome to Choochoo.
    
     You must configure the database before use (no uri).
    
     Please use the ch2 database command.
    


Note that:

  * We specified a maximum amount to drop of 500 bytes (`--max-fwd-len
    500`).  The default is 200, but was insufficient in this case.
    Using a larger value makes the program run slower, so don't do
    this unless necessary.

  * We specified an output file (`-o fixed.fit`).

  * Reading the output above, we can see that the first 4975 bytes of
    data were used.  We will use this in the next recipe.

## See What Data are Dropped

In the recipe above data were dropped after the first 4975 bytes.  We
can see what records that affected as follows:

    > ch2 fit records --after-bytes 4975 myfile.fit
        INFO: Logging to /home/andrew/.ch2/0-35/logs/fit.log
     WARNING: Could not connect to database
    
     Welcome to Choochoo.
    
     You must configure the database before use (no uri).
    
     Please use the ch2 database command.
    


That looks like metadata associated with ending an activity.  Probably
the "stop" button wasn't pressed until some minutes after the activity
ended.  Personally, I see no need to drop this data - it seems like
the jump in timestamps we saw has a reasonable explanation.

## See What Data are Dropped in Detail

Maybe we are a bit more curious about the data above.  What else can
we see?

Notice how the record numbers are `207`, `209`, and `211`.  Since
those are not consecutive there must be some internal messages also
present.  We can display those too:

    > ch2 fit records --after-bytes 4975 --internal myfile.fit
        INFO: Logging to /home/andrew/.ch2/0-35/logs/fit.log
     WARNING: Could not connect to database
    
     Welcome to Choochoo.
    
     You must configure the database before use (no uri).
    
     Please use the ch2 database command.
    


Hmm.  Some message defintions and the checksum.  Nothing very
exciting.

We can also see the same data in binary form.  For example:

    > ch2 fit tokens --after-bytes 4975 myfile.fit
        INFO: Logging to /home/andrew/.ch2/0-35/logs/fit.log
     WARNING: Could not connect to database
    
     Welcome to Choochoo.
    
     You must configure the database before use (no uri).
    
     Please use the ch2 database command.
    


## Remove Arbitrary Data from a FIT File

In the recipe above, perhaps we want to remove the `session` message
and its associated defintion.  This doesn't seem that smart an idea to
me, but it works as an example.

First, we note from the `tokens` dump that the data extend from offset
`5069` to `5316` (the end value is one before the next token at
`5317`).  We can remove that by taking the slices `:5069,5317:` as
follows:

    > ch2 fix-fit myfile.fit --slices :05069,05317: --fix-header --fix-checksum -o sliced.fit
        INFO: Logging to /home/andrew/.ch2/0-35/logs/fix-fit.log
     WARNING: Could not connect to database
    
     Welcome to Choochoo.
    
     You must configure the database before use (no uri).
    
     Please use the ch2 database command.
    


Note that `fix-fit` won't let you remove data that would corrupt the
file (to the best of its ability).

## Change the Times in a FIT File

    > ch2 fix-fit myfile.fit --start '2018-01-01 12:00:00' --fix-checksum -o fixed.fit
        INFO: Logging to /home/andrew/.ch2/0-35/logs/fix-fit.log
     WARNING: Could not connect to database
    
     Welcome to Choochoo.
    
     You must configure the database before use (no uri).
    
     Please use the ch2 database command.
    


The `--start` value sets the first timestamp in the file.  Subsequent
timestamps have the same relative increment as before.

## Search for Values in a FIT File

For some reason we want to know if a file contains any speed values
over 7 m/s:

    > ch2 fit grep -p '.*speed>7' --compact myfile.fit
    usage: ch2 fit grep [-h] [--after-records N] [--limit-records N]
                        [--after-bytes N] [--limit-bytes N] [-w] [--no-validate]
                        [--max-delta-t S] [--name] [--not] [--match MATCH]
                        [--compact] [--context] --pattern MSG:FLD[=VAL]
                        [MSG:FLD[=VAL] ...] [--width WIDTH]
                        PATH [PATH ...]
    ch2 fit grep: error: the following arguments are required: --pattern


## Search for Values in a FIT File with Context

Seeing the results above we'd like to know more about the records
where we were over 7.5m/s:

    > ch2 fit grep -p 'record:enhanced_speed>7' --context myfile.fit
    usage: ch2 fit grep [-h] [--after-records N] [--limit-records N]
                        [--after-bytes N] [--limit-bytes N] [-w] [--no-validate]
                        [--max-delta-t S] [--name] [--not] [--match MATCH]
                        [--compact] [--context] --pattern MSG:FLD[=VAL]
                        [MSG:FLD[=VAL] ...] [--width WIDTH]
                        PATH [PATH ...]
    ch2 fit grep: error: the following arguments are required: --pattern


The search expression has the form `record:field=value` where `record`
and `field` are regular expressions.  If the `:` is omitted then the
record name is ignored.  The comparison can be `=`, `>`, `<` or `~` -
the last of these is for regular expression matching on the value.

## Find FIT Files with Values

This has made us curious.  Do we have any rides where we exceed 17m/s?

    > ch2 fit grep -p 'record:enhanced_speed>17' --match 0 --name *.fit
    usage: ch2 fit grep [-h] [--after-records N] [--limit-records N]
                        [--after-bytes N] [--limit-bytes N] [-w] [--no-validate]
                        [--max-delta-t S] [--name] [--not] [--match MATCH]
                        [--compact] [--context] --pattern MSG:FLD[=VAL]
                        [MSG:FLD[=VAL] ...] [--width WIDTH]
                        PATH [PATH ...]
    ch2 fit grep: error: the following arguments are required: --pattern


The `--name` flag displays filenames on matching, while `--match 0`
means that no matching data are displayed.

## Restrict Displayed Dates

The "usual" display options lets us restrict the range of records or
bytes, but not timestamps (or any other field).  But we can work
around this by using `--grep`:

    > ch2 fit grep -p '.*:timestamp>2018-03-04 11:56:33+00:00' '.*:timestamp<2018-03-04 12:00:00+00:00' -- myfile.fit
    usage: ch2 fit grep [-h] [--after-records N] [--limit-records N]
                        [--after-bytes N] [--limit-bytes N] [-w] [--no-validate]
                        [--max-delta-t S] [--name] [--not] [--match MATCH]
                        [--compact] [--context] --pattern MSG:FLD[=VAL]
                        [MSG:FLD[=VAL] ...] [--width WIDTH]
                        PATH [PATH ...]
    ch2 fit grep: error: the following arguments are required: --pattern


Note that we needed to explicitly include a wildcard record for the
timestamp because the timestamp value itself contains colons - without
the leading `.*:` the left-most colon in the timestamp would have been
taken as the record separator.

Also, it's worth understanding that comparisons with `--grep` are done
via strings *unless* the given pattern can be parsed as a float.

## Read a FIT File in Python

So maybe now we want to know what the maximum speed is in a file?  We
need to write some code to do that...

    from logging import basicConfig, getLogger, INFO
    from ch2.fit.profile.profile import read_fit, read_profile
    from ch2.fit.format.records import no_bad_values
    from ch2.fit.format.read import parse_data
    
    basicConfig(level=INFO)
    log = getLogger()
    
    data = read_fit('myfile.fit')
    types, messages = read_profile(log)
    state, tokens = parse_data(data, types, messages)
    
    SPEED = 'enhanced_speed'
    max_speed = None
    
    for offset, token in tokens:
        record = token.parse_token()
        data = record.as_dict(no_bad_values).data
        if SPEED in data:
            values, units = data[SPEED]
            for value in values:
                if max_speed is None or value > max_speed:
                    max_speed = value
    
    print('Maximum speed: %.2f' % max_speed)

Giving the output

    Maximum speed: 7.80


