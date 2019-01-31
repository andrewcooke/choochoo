
# Other Projects

Could Choochoo help in *your* project?

* [Reading FIT Data on the Command Line](#reading-fit-data-on-the-command-line)
* [Reading FIT Data in Python](#reading-fit-data-in-python)
* [Reading FIT Data for Jupyter](#reading-fit-data-for-jupyter)
* [Matching Spatial Data in Python](#matching-spatial-data-in-python)

## Reading FIT Data on the Command Line

If you have a FIT file (eg from a Garmin watch or bike computer) then
you can use Choochoo to see the contents.

### Requirements

* You must have Python 3.7 (or later) installed.  Check with

      > python --version
      Python 3.7.0

  If necessary, you can get Python from
  [here](https://www.python.org/downloads/).

* You must have Choochoo installed.  For example:

      > python -m venv env
      > source env/bin/activate
      > pip install choochoo

  For more information see [here](getting-started).

### The `fit` Command

Once you have Choochoo installed you can use it to examine fit files.
For example, to extract the latitude and longitude as CSV files:

    > source env/bin/activate
    > ch2 fit --csv -m record -f position_lat position_long -- filename.fit
    Data,7,record,position_lat,-398804040,semicircles,position_long,-842386443,semicircles
    Data,7,record,position_lat,-398804130,semicircles,position_long,-842386685,semicircles
    ...

The units for altitude and longitude are "semicircles".  To get
degrees, multiply by 180 / 2147483648.

### More Information

* For more on the `fit` command try `ch2 help fit`
* To read CSV data into Pandas see
  [here](https://www.shanelynn.ie/python-pandas-read_csv-load-data-from-csv-files/)
* For more examples of what is possible with FIT files see
  [here](fit-cookbook).
* To see all the data in the file, try `ch2 fit --tables filename.fit`

### Possible Risks

If you are considering using this in a project, you might have problems:
* With bugs.  The code is more likely to work on Linux.
* With the data.  Not all FIT files are the same.

Please [contact me](mailto:andrew@acooke.org) if you have problems.

## Reading FIT Data in Python

If you want to program in Python you can use Choochoo as a library to
read data from FIT files inside your program.

### Requirements

* You must have Python 3.7 (or later) installed.  Check with

      > python --version
      Python 3.7.0

  If necessary, you can get Python from
  [here](https://www.python.org/downloads/).

* You must have Choochoo installed.  For example:

      > python -m venv env
      > source env/bin/activate
      > pip install choochoo

  For more information see [here](getting-started).

### Python Code

Here's some example code:

    from logging import basicConfig, getLogger, INFO
    from ch2.fit.profile.profile import read_fit, read_profile
    from ch2.fit.format.records import fix_degrees, no_units
    from ch2.fit.format.read import parse_data

    basicConfig(level=INFO)
    log = getLogger()

    data = read_fit(log, 'data/test/source/personal/2018-07-26-rec.fit')
    types, messages = read_profile(log)
    state, tokens = parse_data(log, data, types, messages)

    LAT, LONG = 'position_lat', 'position_long'
    positions = []

    for offset, token in tokens:
        record = token.parse_token().as_dict(no_units, fix_degrees)
        if record.name == 'record':
            positions.append((record.data[LAT][0], record.data[LONG][0]))

    print('Read %s positions' % len(positions))

The line `record = token.parse_token().as_dict(..)` creates a record
whose `data` is a dict of lists of values.  Then `record.data[LAT][0]`
finds the `position_lat` entry in the dict and takes teh first value
from the list (FIT files can contain multiple values but usually a
field has just one).

The `no_units, fix_degrees` removes the units from the data and
converts the strange "sermicircle" units to degrees (so the latitude
and longitude are in degrees).
        
### More Information

* The code for the library is
  [here](https://github.com/andrewcooke/choochoo/tree/master/ch2/fit).
* To see what data are contained within a FIT file use the [fit
  command](#reading-fit-data-on-the-command-line).

### Possible Risks

If you are considering using this in a project, you might have problems:
* With bugs.  The code is more likely to work on Linux.
* With the data.  Not all FIT files are the same.
* With understanding the library.  It has little documentation and the
  API is unconventional.

Please [contact me](mailto:andrew@acooke.org) if you have problems.

## Reading FIT Data for Jupyter

If you import FIT data into Choochoo you can then explore the data via
Jupyter notebooks.

If you have a FIT file (eg from a Garmin watch or bike computer) then
you can use Choochoo to see the contents.

### Requirements

* You must have Python 3.7 (or later) installed.  Check with

      > python --version
      Python 3.7.0

  If necessary, you can get Python from
  [here](https://www.python.org/downloads/).

* You must have Choochoo installed.  For example:

      > python -m venv env
      > source env/bin/activate
      > pip install choochoo

  For more information see [here](getting-started).

* You must configure Choochoo.  The default should be sufficient.

      > source env/bin/activate
      > ch2 default-config
      
  For more information see [here](getting-started).

### Importing Data

* To import data into Choochoo use the `activities` command:

      > source env/bin/activate
      > ch2 activities filename.fit

### Starting Jupyter

* To start Jupyter use the `jupyter` command:

      > source env/bin/activate
      > jupyter

This will open a page in your web browser.
[Here](https://www.dataquest.io/blog/jupyter-notebook-tutorial/) is a
good tutotial on using Jupyter.

### Accessing the Data

* Inside a Jupyter notebook you can accesss your data as follows:

      >| from ch2.data import *
         s = session('-v 0')
         data = statistics(s, 'Latitude', 'Longitude')
         data.describe()

  This will create a Pandas DataFrame (`data`) with the values for
  latitutde and longitude.

### More Information

* There is more information on accessing data [here](data-analysis).
* Many Jupyter notebooks with examples can be seen
  [here](https://github.com/andrewcooke/choochoo/tree/master/notebooks).
* You can download those notebooks
  [here](https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/andrewcooke/choochoo/tree/master/notebooks)

### Possible Risks

If you are considering using this in a project, you might have problems:
* With bugs.  The code is more likely to work on Linux.
* With the data.  Not all FIT files are the same.
* With understanding Jupyter and how to access the data.

Please [contact me](mailto:andrew@acooke.org) if you have problems.

## Matching Spatial Data in Python

Once you have GPS data in Python you may want to find which points are
nearby.  One way to do this efficiently is to use an RTree, which
works a bit like a Python dict, but with points in two dimensions.
Choochoo includes an RTree library you can use.

### Requirements

* You must have Python 3.7 (or later) installed.  Check with

      > python --version
      Python 3.7.0

  If necessary, you can get Python from
  [here](https://www.python.org/downloads/).

* You must have Choochoo installed.  For example:

      > python -m venv env
      > source env/bin/activate
      > pip install choochoo

  For more information see [here](getting-started).

### Finding Exact Matches

The following code puts Alice at `(1,1)`, with Bob and Charles at `(1,2)`.

      from ch2.arty import CQRTree
      tree = CQRTree()
      tree[[(0, 0)]] = 'alice'
      tree[[(10, 10)]] = 'bob'
      tree[[(10, 10)]] = 'charles'

      def show(tree, x, y):
          found = False
          print()
          for entry in tree[[(x, y)]]:
              found = True
              print('%s at (%g,%g)' % (entry, x, y))
          if not found:
              print('nobody at (%g,%g)' % (x, y))

      show(tree, 0, 0)
      show(tree, 5, 5)
      show(tree, 10, 10)

Here is the output:

      alice at (0,0)

      nobody at (5,5)

      bob at (10,10)
      charles at (10,10)
        
Note that reading from the tree can return multiple values (unlike a
dict).

### Finding Nearby Points

The first example matched points exactly, Instead, we can use the tree
to find *nearby* points:

      from ch2.arty import CQRTree, MatchType
      tree = CQRTree(default_match=MatchType.OVERLAP, default_border=3)
      tree[[(0, 0)]] = 'alice'
      tree[[(10, 10)]] = 'bob'
      tree[[(10, 10)]] = 'charles'

      def show(tree, x, y):
          found = False
          print()
          for entry in tree[[(x, y)]]:
              found = True
              print('%s at (%g,%g)' % (entry, x, y))
          if not found:
              print('nobody at (%g,%g)' % (x, y))

      show(tree, 0, 0)
      show(tree, 5, 5)
      show(tree, 10, 10)

Here is the output:

      alice at (0,0)

      alice at (5,5)
      bob at (5,5)
      charles at (5,5)

      bob at (10,10)
      charles at (10,10)

The `default_border` adds an extra region to all points, so `(0, 0)`
extends from `(-3, -3)` to `(3, 3)`, while `(5, 5)` extends from `(2,
2)` to `(8, 8)`.  Because these overlap we find *everyone* at `(5,
5)`.

### Using Shapes (Lists of Points)

The examples above talk about `(x, y)` points, like `(0, 0)`.  But you
can also store *shapes* as lists of points.  For example, the square
`[(0, 0), (0, 1), (1, 1), (1, 0)]`.

When using shapes the tree uses the smallest rectangle that includes
all the points (called the "Minimum Bounding Rectangle").

(This explains why the points in the examples above are inside lists -
the "points" are really shapes containing a single coordinate.)

### More Information

* The RTree documentation is [here](rtree).
* For large data sets you may need a faster implementation, like
  [this](http://toblerity.org/rtree/) (note that the interface will be
  different to this library).

### Possible Risks

If you are considering using this in a project, you might have problems:
* With bugs.  The code is more likely to work on Linux.
* With understanding the RTree library.

Please [contact me](mailto:andrew@acooke.org) if you have problems.

