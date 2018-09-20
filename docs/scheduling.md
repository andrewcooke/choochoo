
# Scheduling

## Introduction

Various parts of Choochoo - particularly training schedules, but also
reminders and, in the future, possibly summary statistics - use the
idea of "specifications" for repeating events.  These are a compact, textual
way, of defining a calendar-based event that repeats regularly.

## Contents

* [Specifications](#specifications)
* [Schedule Entries](#schedule-entries)

## Specifications

A specification has the form:

    DATE/N[DAYs]START-END
    
for example

    2018-09-20/2w[1mon]2018-01-01-2019-01-01
    
These can be abbreviated and missing start/end dates indicate open ranges.

Intuitively, the above means:

* The "frame" repeats every second week (`2w`).
* The "frame" is such that `2018-09-20` is in the first week
* The specification is valid throughout 2018
* Within the "frame" we take the first Monday (`1mon`)

So the specification is equivalent to "the first Monday of every second 
week in 2018 (including the Monday of the week including 2018-09-20)".

For more details see [this blog post](http://acooke.org/cute/ASpecifica0.html)
(although I don't promise that descriptino is exact - in doubt, see the code).

The UI tries to hide some of the details of these for common cases.

## Schedule Entries

Schedule entries ((which will be displayed in the diary on appropriate days)
are defined with the commands

    ch2 edit-schedules
    
Personally I use two types: "Aim" and "Reminder".  These are defined by default
on an initial install, but can be deleted if needed.
