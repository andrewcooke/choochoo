
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

Pipeline tasks are how Choochoo is extended to calculate new
statistics.  They integrate with Choochoo's internal book-keeping to
re-calculate values when new data are available, or old data are
modified.

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

    This is shown in Figure 1.

    The transformation can be understood in three stages.  First,
    values below a threshol (`zero`) are discarded.  Next, the range
    from this threashold to zone 6 is normalized to the range 0-1.
    Finally, this normalized value is raised to the power `gamma`.

    The "gamma correction" is a standard technique for parameterising
    uncertainty in the shape of a function.  A value of gamma greater
    than 1 will give a "concave" curve - in this case implying that
    high zones are significantly more important than low zones.  A
    value of gamma less than 1 will give a "comvex" curve - implying
    that low zones are similar in importance to high zones.

    By default, the parameter is set to 1.



### Response Calculation
### Results
## Future Work
### Fitting Parameters
### Multiple Components
## Appendix - Getting Started with Choochoo