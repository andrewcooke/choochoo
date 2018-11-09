
# Models

Modelling the realtionship between training and performance is popular
(eg TSS on Training Peaks) and may even be useful.  Here I explore how
this can be added to Choochoo.

* [Scope](#scope)
* [Components](#components)
  * [Impulse Calculations](#impulse-calculations)
  * [Response Calculations](#response-calculations)
  * [Variable Fitting](#variable-fitting)
* [Conclusions](#conclusions)

## Scope

(For now) I am only going to consider "FF Models" - an exponentialy
decaying response to a "training impulse".  Other models exist (eg
PerPot), but are intuitively less clear.  The FF Models are easy to
understand and have wide generality.  This generality is what I want
to explore.

## Components

A practical FF Model (or system of models) requires the following
separable components:

1. Calculation of the impulse
2. Calculation of the respone
3. Variable fitting

My (uninformed) understanding of Training Peaks is that it ignores the
last of these, while the first is fixed to a few inputs.  I feel that
Choochoo could do significantly better.  For example, can we use the
same approach to model recovery to injury?  Does step data predice how
the pain in my leg evolves?

In addition, we require some way of displaying data.  I will rely on
the standard Choochoo solutions for this (showing values in the diary
and plotting data via Jupyter notebooks).  The plotting may require
some extra "smarts" to give smooth curves if we are calculating points
only daily.

### Impulse Calculations

There are two stages here:

* Identifying (eg total steps in day) or calculating (eg HR based
  impulse) some statistics

* Normalization (ie zero point, scaling)

Unfortunately these are not separable.  For example, HR based impulse
requires scaling *before* integration.  This is a problem because we
end up needing normalization in two places: both during calculation of
the HR impulse to give an "input statistic" and when using the input
(HR impulse or steps) in calculation of the response.

Maybe we need a more general abstraction that can dervive one
statistic from another?  This could then be applied to Steps to give,
say, "Step Impulse", while Activity import calculates "HR Impulse"?

### Response Calculations

We need to do this for each component.  This could also be a more
general abstraction that acts on statistics in general.  Input would
have to include constants (which might be calculated in Variable
Fitting).  Or maybe these would also be statistics?

### Variable Fitting

This is still unclear to me.  Need to digest more papers.

## Conclusions

* A more general 'programmable' pipeline for generating new statistics?

* A better understanding of variable fitting.
