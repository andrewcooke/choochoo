
# Training Plans

This is where making Choochoo programmable by end users really comes
into its own.  Take a look at [this
code](https://github.com/andrewcooke/choochoo/blob/master/ch2/plan/british.py)
defining a training plan taken from British Cycling.  It's simple,
declarative code.  You can add your own.

There are also some simple built-in plans available.

* [Existing Plans](#existing-plans)
* [Adding Your Own](#adding-your-own)

TODO - data below incorrect

## Existing Plans

The commands

    ch2 help add-plan
    ch2 plan --list
    
describes the current plans that are available.

The two most basic are:

* **Percent Distance** - this increases the distance each activity by a given
  percentage, starting from a base amount.
  
* **Percent Time** - this increases the time each activity by a given
  percentage, starting from a base amount.
  
Both take a [specification](scheduling#specifications) that defines when the
activities happen.

## Adding Your Own

See the code [here](ttps://github.com/andrewcooke/choochoo/blob/master/ch2/plan/british.py)
for an example.

Please submit pull requests with plans you add.  Together we can build a big, useful library.
