
# Heart Rate Training Impulse

## Survey
### History
### Arbitrary Parameters
### Current Support

https://www.trainingpeaks.com/blog/the-science-of-the-performance-manager/

Limitations.

### Heart Rate v Power

## This Work

### Choochoo

Choochoo is an free, hackable training diary, written in Python, that
runs on a wide variety of computers.  It can import FIT files, process
data with user-provided algorithms, and export results to Pandas and
Jupyter for further analysis and display.

This work extended Choochoo as follows:

* A pipeline task to calculate "HR Impulse" values from Heart Rate
  measurements during exercise.

* A pipeline task to calculate Fitness and Fatigue responses from
  these Impulses.

* A Jupyter notebook to display the results.

Pipeline tasks are Choochoo's extension mechanism for calculating new
statistics.  They integrate with internal book-keeping to re-calculate
values when new data are available, or old data are modified.

The tasks are parameterised using "constants" - parameters that
Choochoo users can modify from the command line.  These allow, for
example, the exponential decay time periods and the scaling factors in
the models to be modified.

### Impulse Calculation

![The Gamma Parameter](gamma.png)

The HR Impulse is calculated in three steps:

1.  Each Heart Rate measurement is converted to a HR Zone following the
    schema used by the [British Cycling
    calculator](https://www.britishcycling.org.uk/membership/article/20120925-Power-Calculator-0).
    
    The calculated zone is a floating point value, numerically equal
    to the zone number at the lower end of the zone, and linearly
    interpolated to the upper end.  So, for example, if zone 3
    extended from 130 to 150 bpm a value of 130 would be given a zone
    value of 3.0 and a value of 140 a value of 3.5.

    Values in zone 1, which has no lower boundary, are all set to 1.0
    (this does not affect the results as these are typically discarded
    when calculating the Impulse - see next step).

    Values above zone 5 are extrapolated assuming that further zones
    have the same width as zone 5.

2.  The zone value above is transformed using the expression:

        zone' = (max(zone, zero) - zero / (6 - zero)) ** gamma

    This is shown in Figure 1 (the `zero` parameter has the value 2)

    The transformation can be understood in three stages.  First,
    values below a threshold (`zero`) are discarded.  Next, the range
    to zone 6 is normalized to the range 0-1.  Finally, this
    normalized value is raised to the power `gamma`.

    The "gamma correction" is a standard technique for parameterising
    uncertainty in the shape of a function.  A value of `gamma`
    greater than 1 will give a "concave" curve - in this case implying
    that high zones are significantly more important than low zones.
    A value of `gamma` less than 1 will give a "comvex" curve -
    implying that low zones are similar in importance to high zones.

    By default, the `gamma` parameter is set to 1 and `zero` to 2.

3.  The impulse is calculated as:

        impulse = zone' * delta_t

    where `delta_t` is the time (in seconds) between this measurement
    and the next.  In a typical FIT file `delta` is around 10s; if it
    exceeds a configurable cutoff (`max_secs`, default 60s) then no
    impulse is calculated.  This avoids calculating incorrect, high
    impulses when the data feed drops.

The `gamma` and `zero` parameters allow us to encode beliefs about the
physiological processes we are modelling.  For example, if we believe
that only intensive exertion is effective, we can raise `zero` to 3 or
4.  And if we feel that all exertion above that point should be
weighted roughly equally then we can lower `gamma` to, say, 0.1,
giving a curve that approximates a "top hat" response.

### Response Calculation

![Response Calculation](response.png)

The response is calculated by integrating each impulse and then
decaying with the appropriate time constant as time increases.  In
addition, an arbitrary scale factor can be applied.

By default, the time period (`tau_days`) is taken as 7 for Fatigue and
42 for Fitness.  The `scale` factor is 5 for Fatigue and 1 for Fitness
(chosen arbitrarily so that the two values cover similar ranges).

In the figure Impulses are represented by area (so the y axis is
Impulse / duration).  It is just possible to make out the increments
in the Fatigue and Fitness responses as they integrate the Impulse
data.

### Results
## Future Work
### Fitting Parameters
### Multiple Components
## Appendix - Getting Started with Choochoo