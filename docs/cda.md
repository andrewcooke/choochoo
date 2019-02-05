
# Measuring CdA

When you're cycling your energy is general spent either climbing hills
or pushing air out of the way - those are the two big "sinks" of
energy.

To estimate power we need to estimate these.  The first - climbing
hills - is easy [given elevation data](elevation).  The second depends
on your speed (squared), the cross-section area you present (`A`), and
a constant (`Cd`).  The area and constant together are known as `CdA`.

Here I describe how to measure `CdA`.

* [Previous Work](#previous-work)
* [A Statistical Approach](#a-statistical-approach)
  * [Physics](#physics)
  * [Coasting](#coasting)
  * [Calculating CdA and Crr](#calculating-cda-and-crr)
  * [Data Exploration](#data-exploration)
  * [Final Measurement](#final-measurement)
* [Summary](#summary)

## Previous Work

It turns out that I'm not the first to have thought of this.  [This
document](https://github.com/andrewcooke/choochoo/blob/master/data/dev/indirect-cda.pdf)
describes an approach to measure both `CdA` and `Crr` (rolling
resistance) by making test rides.

## A Statistical Approach

However, I'm stuck at home injured, so I want to derive `CdA` from
"normal" ride data I already have, without a power meter.

### Physics

The physics is pretty simple.  If we know the bike's height and speed
at two different points, and the distance between them, then:

  * The total energy "added" to the system is the gravitational
    potential energy from a drop in height (going downhill) *plus* any
    extra work done pedalling.

  * The total energy "removed" from the system is via aerodynamic drag
    *plus* braking *plus* rolling resistance.

  * The difference between energy input and output will be seen as a
    difference in speed before and after (kinetic energy).

That's a fair number of variables, but we can simplify things by:

  * Only using data where the ride is not pedalling (where cadence is
    low).

  * Assuming that there is no wind (which would affect aerodynamic
    drag).

  * Ignoring rolling resistance (which should be relatively small).

  * Treating the braking as "noise".  This will become clearer later,
    but basically we can hope that braking will be seen as erroneous
    measurements that give high `CdA` values.

    Another way of saying this is that we will divide the ride into
    many small sections.  In some the rider will be braking, and those
    will give bad results.  But hopefully there are enough sections
    without braking that we can see some kind of consensus emerge.

### Coasting

First, we need to find sections of the ride where the rider is not
pedalling.  For this we need the cadence sensor.

The SQL query
[here](https://github.com/andrewcooke/choochoo/blob/master/ch2/stoats/calculate/cda.py#L39)
is intimidating, but not as complex as it looks.  It is trying to find
start and finish points (`s` and `f`) where:

  * The cadence is less than `max_cadence` at those points and at all
    points between.

  * Outside the two points (at `ss` and `ff`) the cadence is more than
    `max_cadence` (so we have the largest section possible).

  * All points are in the same "timespan" (lap / autopause block).

  * The average speed across the whole segment is at least
    `min_speed`.

  * The total time across the whole segment is at least `min_time`.

Segments found are added to the ActivityBookmark table.

### Calculating CdA and Crr

Once we have found the segments we can look at each "step" (recording
interval) in the segment.  At the start and end of each step we know
the location, distance and speed (`v`), so we can calculate:

  * [Elevation](elevation) change, `h`.

  * The distance travelled, `d`.

  * The gravitational potential energy gained (or lost, if climbing).
    This is `m x g x h` where `m` is mass (rider and bike) and `g` is
    gravittaional acceleration (9.8 m/s).

  * The kinetic energy before and after (`1/2 x m x v^2`).

  * The average of the squared speed `avg_v2`, assuming that speed
    varies linearly (constant acceleration).  You ened to do a little
    calculus for this, but it turns out that it's `v_a^2 + v_a x v_b +
    v_b^2` where `v_a` is the speed at the start and `v_b` the speed
    at the end.

  * The loss in energy due to air (`CdA x p x avg_v2 x d`) where `p`
    is air density (1.225kh/m^3).

  * The loss in energy due to friction (`Crr x d`).

### Data Exploration

From the energy balance described [above](#physics) we know that the
change in energy can be attributed to resistance from air *plus*
friction.  If we don't know `CdA` or `Crr` then all we have is their
sum.  This means that, for each step we can plot a line on the graph
of `CdA` n `Crr` (the line shows all points that sum to give the same
energy loss).

That plot looks like this:

![](cda-crr-1.png)

Zoomed in on the x-axis (`CdA`) we can see:

![](cda-crr-2.png)

There's clearly a peak around a value of `CdA` at something like 0.6.
But there's no evidence of any kind of preferred value in the y
direction.

I was hoping (optimistically) that we would see a preference for a
certain value of `Crr` (ie more lines crossing at a certain y value)
because the different dependency on speed for the two coefficients
means that they should be distinguisable in observations made at
different speeds.  But I think here we're just getting too much noise
from braking (ehich we can't control for, and which appears as rolling
reistance).

### Final Measurement

Given the above, we'll assume `Crr` is zero and calculate `CdA` alone.
This is equivalent to counting the number of lines that cross the x
axis in the plot above.  Viewed as a histogram:

![](cda-poly.png)

The curves are polynomials fit to the data - a way of smoothing the
data to find the maximum.  From those, the maximum is somewhere around
0.52 or 0.53.

## Summary

The data suggest that my `CdA` is around 0.52 or 0.53.  Searching the
'net it seems typical values for a road bike are around 0.3 to 0.4, so
a value of 0.5 for an MTB doesn't seem too surprising.

And, more than that, to get an answer so "close" suggests the method
is reasonable.

The notebook used in the analysis is available
[here](https://github.com/andrewcooke/choochoo/blob/master/notebooks/power/plot_cda_k.ipynb).