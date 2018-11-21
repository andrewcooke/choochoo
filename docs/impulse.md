
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
runs on a wide variety of computers.  It can import data from FIT
files, run arbitrary code to process the data, and export results to
Pandas and Jupyter for further analysis and display.

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
### Response Calculation
### Results
## Future Work
### Fitting Parameters
### Multiple Components
## Appendix - Getting Started with Choochoo