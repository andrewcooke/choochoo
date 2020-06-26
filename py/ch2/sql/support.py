
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import expression, case
from sqlalchemy.types import Numeric

Base = declarative_base()


# https://docs.sqlalchemy.org/en/13/core/compiler.html


class greatest(expression.FunctionElement):
    type = Numeric()
    name = 'greatest'


@compiles(greatest)
def default_greatest(element, compiler, **kw):
    return compiler.visit_function(element)


@compiles(greatest, 'sqlite')
@compiles(greatest, 'mssql')
@compiles(greatest, 'oracle')
def case_greatest(element, compiler, **kw):
    arg1, arg2 = list(element.clauses)
    return compiler.process(case([(arg1 > arg2, arg1)], else_=arg2), **kw)
