
# Expressions

Driven by [physiological models](models) it would be nice to have some
way of generating dervied statistics from arbitrary expressions.  Here
I explore how this would work.

* [Explotaion](#exploration)

## Exploration

    Statistic * 2

Multiply today's value of `Statistic` by 2.

    "Statistic Name" * 2

Quoting the name for spaces.  Are we going to support strings?  More
generally how do we handle types at all?

Is the name sufficient to identify the statistic?  Do we need owner
too?  What about constraint?  Think, for example, of TSS scores for
indivdual activity groups.  Does that make sense?

    Statistic[-1d] * 2

Multiply yesterday's `Statistic` by 2.  Are we going to support
arrays?

    Statistic[-(3-2)d] * 2

Would that work?  What does the `d` mean?  How does this affect types?

    "New Statistic" = Statistic * 2

Do we need to specify the result in the expression?  Do we support
multiple expressions?

     Statistic = Statistic * 2

What would this mean?

    (Statistic ^ 3) - 1.5

Nesting.  Common arithmetic operations.  Do we need to worry about
conflicts with bitwise logic?

     sin(Foo) * myfunc(Statistic)

Common functions.  What about user defined functions?

Do we support multiple values for input?  What about for output?  How
do we unpack multiple return values?  Do we need to bind to
expressions?

    a = sin(Foo); "New Statistic" = 3 * a

Why isn't `a` a statistic here?

    let a = sin(Foo); "New Statistic" = 3 * a

    $a = sin(Foo); "New Statistic" = 3 * $a

How general do we want this to be?  Is it going to be a separate
library?  Or tied to Choochoo?

    Statistic = FTHR * 3

If `FTHR` is a constant, what does this mean?  Constants are
statistics.  So maybe...

    Statistic = FTHR[<]

where `[<]` means preceding value?  And `[2018-01-01]` would be for a
specific date?  And `[-1m<]` would be latest value older than a month?

Does `[-1d]` mean exactly one day ago?  Anything within the last day?
The last 36 hours?  Do we want `[-1]` to just mean "whatever came
before"?

[https://pythonhosted.org/dynts/dsl/index.html](https://pythonhosted.org/dynts/dsl/index.html)
is a DSL for time series.

What about integration?  Seems like might be useful for FF models?
Should the time of values be more explicit?  So `Statistic[-1m:]` is
all values in the last month?

