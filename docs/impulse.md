
# Heart Rate Training Impulse

## Introduction

### Aims

I'm writing this article for a couple of reasons.

First, I want to explain and de-mystify the FF-Model.  I get the
impression many people don't understand quite how *simple* it is.
Following from that, maybe people aren't understanding exactly what it
shows, or how it can or should be used.

Second, I want to showcase Choochoo - a *hackable* training diary.
Choochoo is written for people at the intersection between sport and
computing / maths / science.  People who want to experiment, get their
hands dirty, and build their own, personal, customized approach.

So I'm going to show how Choochoo implements the FF-Model.  How the
calculations are made, what they mean, and how they might be tweaked.
I'll end with some questions that people might want to explore -
questions that I hope to explore using this software.

### The Theory

#### Overview



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

(This is all for Linux.  Something similar should work for OSX.  On
Windows it shouldn't be *too* different...)

### Install

First, you need Python 3.7 installed.  Check your version:

    > python --version
    Python 3.7.0

If necessary, you can get the latest version of Python
[here](https://www.python.org/downloads/).

Next, you need to create a "virtualenv".  This is a copy of Python
where Choochoo will be installed (so it doesn't mess with anything
else you might want to do in Python).

    > python -m venv env

Next enable that:

    > souce env/bin/activate

Your prompt should now show `(env)`.  When you see that you're using
the local copy of Python.  You will need to do this whenevr you want
to use Python and Choochoo.

With all that preparation done, we can install Choochoo:

    > pip install choochoo
    [...]
    
That should display a lot of messages but, hopefully, no errors.

Once done, you can run Choochoo:

    > ch2
	INFO: Using database at ...
	INFO: Creating tables

     Welcome to Choochoo.

     Before using the ch2 command you must configure the system.

     Please see the documentation at http://andrewcooke.github.io/choochoo

     To generate a default configuration use the command

	 ch2 default-config

     NOTE: The default configuration is only an example.  Please see the docs for
     more details.

### Configure

So create a default database:

    > ch2 default-config
    
### Load Data

Read your FIT files:

    > ch2 activities /path/to/FIT/files/*.fit

(This will take some time and, I'm afraid, might give errors.  As far
as I know. I am the only user, so if you're following these
instructions you're my first tester...  Please raise issues
[here](https://github.com/andrewcooke/choochoo/issues) if something
goes wrong.).

### Plot Data

If you've got this far, congratulations!  Now we can start Jupyter and
plot the results in your browser:

    > jupyter notebook

This should open a new page in your browser.  Select
ch2/data/notebooks and then click on TODO

## Appendix - The Author

I'm adding because I don't want to mislead.  I'm no expert on this
stuff.  The details above come from papers I've found on-line.  I
could have misunderstood.  So check things out for youself.  I've
collected some of the papers
[here](https://github.com/andrewcooke/choochoo/tree/master/data/training).

If you came here actually expecting to find something out about me,
well... way, way back in the day I got a PhD in Astronomy, but most of
my working life has been spent programming computers.  I also like to
ride my bike, when I'm not injured.
