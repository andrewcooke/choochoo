
# Diary

## Introduction

The diary is where you record daily stats, see reminders, and access
information about recent activities.

![](diary.png)

In the screenshot above you can see:

* top left, the calendar used for date selection / navigation
* top right, the general info area
* current injuries, including the ability to track pain (rated 0-9)
* details for an activity, imported from a FIT file. with colour
  coding based on monthly statistics

## Contents

* [Navigation](#navigation)
* [Calendar](#calendar)
* [General Info](#general-info)
* [Injuries](#injuries)
* [Activities](#activities)

## Navigation

At any moment a single area of the display is highlighted.  This is the
*focus*, and it is where text is entered.  The focus can be moved using
the cursor keys.  On many systems it will also be possible to change focus
by clicking with the mouse.

A "higher level" of movement is possible using Tab (and Shift-Tab).  This
moves through the most important areas of the screen in sequence.  These
jumps may ba larger than those made with the cursor keys.  For example, a
single Tab press moves the focus away from the calendar, while the cursor
keys change focus within the calendar.

To quit the diary use Alt-q or Alt-x (the latter quits without saving and
edits made to the current display).

## Calendar

Moving to a specific date (numbered day) and pressing Space or Enter will
select that day.  On the month and year + and - will advance / retreat
and single digits will make appropriate advances.  On the month letters
will cycle through month names that start with that letter.

Selecting the = (top left) gives the current date.  The < and > move
backwards and forwards by day (Space, Enter or d), month (m) or year (y).

## General Info

Select a field (eg using Tab) and then type the data you want.  Generally
fields will not accept invalid data.  In some cases (eg weight) out-of-range
values are needed during entry of the "complete" value.  Out of range values
are highlighted in red and will not be saved to the database.

Underscores represent "empty" fields.  These are NULLs in the database.

## Injuries

Injuries can be modified  via `ch2 edit-injuries`.  Once defined they
are displayed in the diary.

## Activities

Reading activities is described [here](activities).

The colour scheme, although not beautiful, is easy to remember:
white is the "top" of the scale, moving down through red, yellow 
and green (think traffic lights), with grey at the bottom.  The
colouring of the HR zone bar graph is a visual reminder.

Coloured backgrounds indicate high rankings for the month or year
(depending on how the summaries are calculted).  So white background is
the highest; red second highest etc.  Black background values are
coloured by quintile (white top quintile, red second, etc).
