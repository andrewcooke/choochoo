
# Equipment Tracking

* [Introduction](#introduction)
* [Defining a New Item](#defining-a-new-item)
* [Adding Parts](#adding-parts)

## Introduction

Let's walk through a simple example.  First I will add my Cotic bike:

    > ch2 kit new bike cotic
        INFO: Version 0.24.3
        INFO: Using database at database.sql
    CRITICAL: Specify --force to create a new type (bike)
        INFO: See `ch2 help` for available commands.
        INFO: Docs at http://andrewcooke.github.io/choochoo


All the string arguments here are free-form - we can choose whatever
terms we want - but the system checks against existing terms.  In this
case we're introducing a completely new *type* (think bike, shoes,
tent, etc) and so the `--force` flag is needed for confirmation.
Adding future bikes will not require this, because `bike` will already
be known by the system..

    > ch2 kit new bike cotic --force
        INFO: Version 0.24.3
        INFO: Using database at database.sql
     WARNING: Forcing creation of new type (bike)
        INFO: Created bike cotic


Now I have a bike I am going to add some inner tubes at various dates.

    > ch2 kit add cotic front-tube michelin 2019-01-01
        INFO: Version 0.24.3
        INFO: Using database at database.sql
    CRITICAL: Specify --force to create a new component (front-tube)
        INFO: See `ch2 help` for available commands.
        INFO: Docs at http://andrewcooke.github.io/choochoo


Again the syste catches the first use of `front-tube` so we flag that
it is OK with `--force`.

    > ch2 kit add cotic front-tube michelin 2019-01-01 --force
        INFO: Version 0.24.3
        INFO: Using database at database.sql
     WARNING: Forcing creation of new component (front-tube)
     WARNING: Part name michelin does not match any previous entries
        INFO: Added cotic front-tube michelin at 2019-01-01 00:00:00


    > ch2 kit add cotic front-tube michelin 2019-03-01
        INFO: Version 0.24.3
        INFO: Using database at database.sql
        INFO: Expired previous front-tube (michelin) - lifetime of 59days 0h00m00s
        INFO: Added cotic front-tube michelin at 2019-03-01 00:00:00


    > ch2 kit add cotic front-tube vittoria
        INFO: Version 0.24.3
        INFO: Using database at database.sql
     WARNING: Part name vittoria does not match any previous entries
        INFO: Expired previous front-tube (michelin) - lifetime of 224days 21h17m18s
        INFO: Added cotic front-tube vittoria at 2019-10-11 21:17:18


That's three different inner tubes on the front.  The last uses
today's date as a default - that makes it easy to note changes at the
command line as you do the work.

Also, it's worth noting that previous tubes are *expired* as new ones
are added.  You don't need to add the tubes in order - however they're
added, the start and end times should align correctly.

