
2019-12-03

# Fitting SHRIMP Decay

The decay time in the [SHRIMP](impulse) model may vary by person,
sport, age, etc.  Here I describe a Jupyter template that lets you
measure the parameter using [segment](segments) speeds.

## Contents

  * [Prerequisites](#prerequisites)
  * [Using The Template](#using-the-template)
    * [The Command](#the-command)
    * [Understanding The Results](#understanding-the-results)
  * [Conclusions](#conclusions)

## Prerequisites

The [SHRIMP](impulse) model tries to measure 'fitness'.  The following
template assumes that 'fitness' is similar to speed on known
[segments](segments).

So this is only going to work if you (1) define at least one segment
and (2) regularly ride (or run I guess) that segment, as fast as your
are able at that time.

## Using The Template

### The Command

For the segments `Pedro de Valdivia`, `Pio Nono` and `Juan Pablo II`
(which are the climbs I regularly test myself on) I use the command

    > ch2 jupyter show fit_ff_segments 'Pedro de Valdivia' 'Pio Nono' 'Juan Pablo II'

After running the cells I see:

![](fit-segments.png)

### Understanding The Results

It's probably worth viewing the image directly and reading through.
I'll discuss the various sections below.

#### Load Data

These are quite complex queries so that we isolate exactly the data we
require.  Thankfully you should not have to change these.

#### Define Plot Routine

A plotter that shows the reponse, the performances, and which data
were discarded during the fit.

#### Plot Initial Response

Here I display what the default 42 day delay (with effectively zero
start value) looks like.

The black line is the calculated response (ie 'fitness').  The
coloured dots are 'performances'.  The performances are related to my
speed over the segments, but each segment has separate scaling and
offset to best-fit the response.

This may seem odd.  Why are we scaling and offsetting the observations
to fit the model?  The reason is that the relationship between
'performance' and speed is not clear.  How fast would you be with 'no
fitness'?  Why would a particular fitness give the same speed on
different segments?  These kinds of questions mean that we can only
use variations within a segment - we cannot directly compare different
segments - and this, effectively, is what giving each segment an
indvidual scaling and offset does.

#### Explore Effect of Start

In these plots I vary the start parameter.  It is interesting to see
that this affects only the initial fitness levels - the effect soon
'dies out'.  This suggests that the initial levels is (1) not that
important and (2) not very well constrained by the data.

#### Fit Model using L1

This is the meat of the analysis.

First, we fit the period alone, and then we fit period and start value
together.

Using an L1 norm means that we minimize the absolute difference
between the model and observations (more exactly, it is the absolute
difference divided by the model).  This is more forgiving than the
usual L2 norm (below) and more appropriate for noisy data where we
don't really understand the noise distribution.

The threshold is given as two values (hi, lo).  This means that
observations will be rejected if they are more than `hi` above the
model or `lo` below.  I use asymmetric thresholds because we want to
reject slow rides that are simply unrepresentative of how fit I was.

Rejected points are marked on the plot with an "X".

Because the entire process is somewhat ad-hoc there is no way to
determine when to stop rejecting points.  One approach might be to
stop when the result appear stable.  In this case that appears to be
with a period of 45.1 days.

#### Fit Model using L2

The L2 norm reduces the deviation squared (more exactly, it is the
square deviation divided by the model).  This is roughly equivalent to
assuming a normal error distribution.

The thresholds need to be modified for the new norm, but are again
asymmetric.

## Conclusions

* The start value is relatively unimportant.

* The period is poorly constrained by the data and consistent with the
  widely used value of 42 days.
