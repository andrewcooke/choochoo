
# Equipment Tracking

* [Introduction](#introduction)
* [A More Complete Example](#a-more-complete-example)
* [Theory - Making Things General](#theory---making-things-general)
* [Loading Activities](#loading-activities)
* [Command Reference](#command-reference)
  * [kit start](#kit-start)
  * [kit finish](#kit-finish)
  * [kit delete](#kit-delete)
  * [kit change](#kit-change)
  * [kit undo](#kit-undo)
  * [kit show](#kit-show)
  * [kit statistics](#kit-statistics)
  * [kit rebuild](#kit-rebuild)

## Introduction

### Bike Components

I keep forgetting to track when I modify equipment on my bike.  This
is annoying, because I would like to know if certain models of
components (chains, particularly) last longer than others.

So I wanted to make a solution that made my life as simple as
possible.  The result is a command line tool where I can type

    > ch2 kit change cotic chain pc1110

when I add a SRAM PC1110 chain to my Cotic bike, and everything else
is done for me, automatically.

If I want statistics (how far I've ridden, how long it's lasted) on
chains, I can type:

    > ch2 kit statistics chain

And if I want statistics on that particular model:

    > ch2 kit statistics pc1110

### Shoes

I'm not so bothered about shoes, but I know many runners are, and
supporting them was my second use case.

Unlike bike components, buying a second pair of shoes doesn't
necessarily replace the first pair.  So you have to expire these
automatically:

    > ch2 kit start shoe ultraboost-19
    > ch2 kit start shoe zoom-pegasus
    > ch2 kit finish ultraboost-19
    > ch2 kit statistics shoe

## A More Complete Example

First, I will add my Cotic bike:

    > ch2 kit start bike cotic --force
        INFO: Version 0.25.5
        INFO: Using database at database.sql
     WARNING: Forcing creation of new group (bike)
        INFO: Started bike cotic at 2019-10-27 16:57:17


We're introducing a completely new *group* (bike) and so the `--force`
flag is needed for confirmation.  Adding future bikes will not require
this, because `bike` will already be known by the system..

Now I have a bike I am going to add some inner tubes at various dates.

    > ch2 kit change cotic front-tube michelin 2019-01-01 --force
        INFO: Version 0.25.5
        INFO: Using database at database.sql
     WARNING: Forcing creation of new component (front-tube)
     WARNING: Model michelin does not match any previous entries
        INFO: Changed cotic front-tube michelin at 2019-01-01 00:00:00


Again the system catches the first use of `front-tube` so we flag that
it is OK with `--force`.

    > ch2 kit change cotic front-tube michelin 2019-03-01
        INFO: Version 0.25.5
        INFO: Using database at database.sql
        INFO: Retired previous front-tube (michelin)
        INFO: Changed cotic front-tube michelin at 2019-03-01 00:00:00


Previous tubes are *retired* as new ones are added.  You don't need to
add the tubes in order - however they're added, the start and end
times should align correctly.

    > ch2 kit change cotic front-tube vittoria
        INFO: Version 0.25.5
        INFO: Using database at database.sql
     WARNING: Model vittoria does not match any previous entries
        INFO: Retired previous front-tube (michelin)
        INFO: Changed cotic front-tube vittoria at 2019-10-27 16:57:26


That's three different inner tubes on the front.  The last uses
today's date as a default - that makes it easy to note changes at the
command line as you do the work.

Now we can see the statistics:

    > ch2 kit statistics front-tube
        INFO: Version 0.25.5
        INFO: Using database at database.sql
    Item front-tube
    +-Model michelin
    | +-Lifetime
    | | +-Count 2
    | | +-Sum 299d 16h57m26s
    | | +-Average 149d 20h28m43s
    | | `-Median 149d 20h28m43s
    | +-Active Time
    | | +-Count 2
    | | +-Sum 0s
    | | +-Average 0s
    | | `-Median 0s
    | `-Active Distance
    |   +-Count 2
    |   +-Sum 0m
    |   +-Average 0m
    |   `-Median 0m
    `-Model vittoria
      +-Lifetime 2s
      +-Active Time 0s
      `-Active Distance 0m


In this example (which is auto-generated from the commands) there were
no activities loaded (and because this code is new I don't have any
'real' data to share either), but you can see that of activities were
available there would be statistics on active distance and time.  For
more details on how this works see [Loading
Activities](#loading-activities).

## Theory - Making Things General

Choochoo can track *anything* that fits into this schema:

**Groups** These are the *kinds of things* you track: shoes, bikes,
etc.

**Items** These are the particular things: the name you give to a
particular bike, or a particular pair of shoes.  At this level, items
need to be retired explicitly.

**Components** These (optionally) make up the things you are tracking.
So "chain", for a bike, or "shoelaces" (maybe!) for shoes.

**Models** These describe a particular component.  So the chain migbt
be "PC1110".  At this level, components are retired automatically
(when they are replaced).

Note that all these names can contain spaces, but if you use spaces
you need to take care with quotes on the command line.  I find it's
simpler to use dashes.

Also, names must be unique.  You cannot re-use the same name for
different things.

## Loading Activities

The software has to 'know' what kit is used in what activitiy.  This
is done by defining the aviable `kit` when you load the activity.

So, for example, if all the fit files in directory `mtb-rides` are
from rides on my Cotic bike (defined with `ch2 kit start cotic`), then
I can load them all with:

    > ch2 activities ./mtb-rides/*.fit -Dkit=cotic

This will populate the appropriate statistics using the kit defined
before the data were loaded.  If you modify the kit (eg by using `kit
change`) then you can rebuild the statistics with the
[rebuild](#kit-rebuild) command.

## Command Reference

Don't forget you can do

    > ch2 kit *command* -h

for more information.

### kit start

Define a new [item](#theory---making-things-general).

Use this to define a new bike, pair of shoes, etc.  You can provide a
date if necessary; if not, it is assumed that you are starting to use
this item from "now".

### kit finish

Retire an [item](#theory---making-things-general).

Indicate that you are no longer using the bike, shoes etc.  For
example, you've crashed the bike or thrown the shoes away.  Again, you
can provide a date if you stopped using the item some time ago (the
default is "now").

### kit delete

Remove all information about an [item](#theory---making-things-general).

You might do this if you made a spelling mistake when starting a new
item, for example.

### kit change

Indicate that you have changed a
[component](#theory---making-things-general) by giving the new
[model](#theory---making-things-general).

For example if you change the chain on your bike that you care
calling "trek", and the new chain is SRAM PC110, you might type

    > ch2 kit change trek chain sram-pc1110

The `chain` is the *component* and `sram-pc110` is the *model*.

You can give a date, or you can use `--start` to indicate that this
describes how the item was initially.

When you change a component the previous model is automatically
retired.

### kit undo

Removes information added by [change](#kit-change).

The optional date (default "now") helps identify which model to
remove.  The previous model will be "unretired" as appropiate.

### kit show

Show the structure (groups, items, components and models) defined.

A date can be given; the default is "now".

### kit statistics

Show the statistics for the named kit.  The name can be a group, item,
component or model.

### kit rebuild

Rebuild the statistics associated with
[activities](#loading-activities).


