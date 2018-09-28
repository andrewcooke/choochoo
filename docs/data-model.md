
# Data Model

## Introduction

Choochoo is all about the data.  In particular - getting stats that you can
analyse and use to improve performance.  The data model (by which I mean how
the data are rganised in the database) is a key part of this.  We a model that
is flexible enough to capture anything that might be important, simple enough
that analysis doesn't have many special cases, and which helps avoid
inconsistent and stale values.

## Contents

## Inheritance

The use of inheritance in the table schema is driven by the need to balance
flexibility - a variety of different types and structures - with "freshness" -
it must be simple to "expire" stale data.  The former pushes towards many
types; the latter towards few types connected by "on delete cascade".
Inheritance resolves this conflict by associating multiple types with a single
(base) table.

For more details on inheritance and the SQLAlchemy approach used, please see
[Joined Table
Inheritance](https://docs.sqlalchemy.org/en/latest/orm/inheritance.html#joined-table-inheritance)
in the SQLALchemy docs.

There are two important type hierarchies in the code:

* **Statistics** has a base table, which contains values and times and is used
  for analysis.  
