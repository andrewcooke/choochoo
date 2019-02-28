
We need something that, for example, lets us calculate power depending
on the bike used.

To solve this seems quite complex.

We need a way to track bikes.  That might be a constant, which can
itself be a JSON struct, existing at various times (modified
equipment, say).

Each bike would have a different constant name.

Then on loading you could specify some other constant, say the
'BikeUsed'.  So the loading might look like

    ch2 activities --D BikeUsed Cotic **/*.fit

which would imply that all those activities have BikeUsed=Cotic (ie
the corresponding statistic is set).

May be issues with owners and deletion here.  How are these deleted
when the activity is deleted?  Does that conflict with the owner being
a constant?  Do constants need to be sources?  What happens if a
constant is deleted?

Assuming the above works, how do we get from BikeUsed=Cotic to a mass
for power?

The power config is also via a constant can could be:

  power = {'m': '$BikeUsed.mass + $Weight', ...}

where $BikeUsed.mass looks up the mass entry of the constant named by
BikeUsed and $Weight looks up the Weight entry (latest) from the
diary.

Need to be a bit more exact here.

  $BikeUsed.mass seems like it sould substitute down to Cotic.mass

maybe we need

  $$BikeUsed.mass -> $Cotic.mass -> value

What is binding strength of "."?  Maybe $$BikeUsed.mass is
$($BikeUsed.mass) rather than $$(BikeUsed).mass?  Maybe use {}
instead?

So {BikeUsed}.mass is "Substitute BikeUsed and then ..."  What?

Maybe it should be {BikeUsed}['mass']

Then everything would be handled by JSON?

If we're using JSON don't use {}.  How about backquotes?

   `BikeUsed`['mass']

where `BikeUsed` is substituted as {'mass': 12, ...} say.

Does JSON support arithmetic?  Need to do the addition.

Orrr... skip the addition and have two parameters for mass.  That
would be simpler.  But we still have substitution and de-referenceing
that aren't handled by JSON.

Hmmmmm

Or.... constants support arbitrary classes.  Maybe we use some special
arbitrary class for this particular use case?  How much config
flexibility do we need?

Maybe the constant is

  power = {'m': ['BikeUsed', 'Weight'], ...}

and it knows to look those up?  Does the class instatntiation get a
database session?  Seems like it could do, because it's in Python -
just passed a JSON decoded blob.

In fact, we could have some kind of middle ground, where it supports
some kind of $ syntax and does lookups, but it otherwise a named
tuple.

So

  power = {'bike': '$BikeUsed', 'weight': '$Weight'}

would expand those two variables and the code might then have
something like:

  mass = power.bike.mass + power.weight

But that has an implicit JSON expansion for BikeUsed.  Make that explicit:

  power = {'bike': '#Bike($BikeUsed)', 'weight': '$Weight'}

to use the Bike namedtuple.  But that has namepace issues....  maybe
just stick with JSON?

  power = {'bike': '#$BikeUsed', 'weight': '$Weight'}

or just 

  power = {'bike': '#BikeUsed', 'weight': '$Weight'}

if we never want JSON expansion without substitution.

What about recurrance?  If something evaluates to $....  For now, no.

Implementing...

So we really need owner and constraint.

In some cases those could be encoded in the name:

  power = {'bike': '#BikeUsed:owner:constraint', 'weight': '$Weight'}

but always?  Maybe this is best for now?

  power = {'bike': '#owner:name:constraint', 'weight': '$Weight'}

OK, so maybe FTHR.Bike should be the same syntax as name:constraint?
and constraint should be required?  and maybe 'ActivityGroup "Bike"'
is too much?  or should be supplied in this case?  NO Those are just
names - the ".Bike" is just a convention.
