
# FIT Files

## Introduction

The FIT format is used by ANT+ hardware (bike computers, smart
watches, sensors) to transmit and store data.  If you are curious
about the technical details, see the
[SDK](https://www.thisisant.com/resources/fit).

Choochoo includes a library that reads (but does not write) FIT format
data.  This can be used by third parties (see the API docs below), but
is intended mainly to allow data to be imported into the ch2 diary.
However, this is not yet implemented - currently all that is possible
is displaying the data in a variety of formats.

## Contents

* [Displaying FIT data](#displaying-fit-data)

  * [The `records` format](#the-records-format) (the default) - this
    shows the file contents in a high-level, easy-to-read format.
  
  * The `messages` format - this displays the low-level binary data and
    is mostly of use when debugging errors.

  * The `fields` format - a more detailed low-level display that is also
    mostly used for debugging.

  * The `csv` format - used to compare test data with the examples
    provided in the [SDK](https://www.thisisant.com/resources/fit).

* Third-party API use

* Implementation and limitations

## Displaying FIT Data

### The `records` Format
